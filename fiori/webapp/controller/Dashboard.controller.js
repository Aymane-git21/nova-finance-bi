sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/core/ValueState"
], function (Controller, ValueState) {
  "use strict";

  return Controller.extend("novaspace.cockpit.controller.Dashboard", {

    onInit: function () {
      // Chart properties are set in code rather than in the view: they are
      // presentation detail, and burying forty lines of vizProperties in XML
      // makes the view unreadable for no benefit.
      //
      // Applied only once every model has finished loading, and that ordering
      // is not optional. Setting them on view-loaded looked correct and was
      // not: the JSON models resolve asynchronously, VizFrame recomputes its
      // axis scale when data arrives, and the fixed 0-100% ranges below were
      // silently overwritten. The chart came out with a 0-120% x-axis against
      // a 0-150% y-axis - which means "on plan" was no longer the 45-degree
      // diagonal the subtitle tells the reader to look for.
      //
      // dataLoaded() rather than attachRequestCompleted(): it resolves
      // immediately for a model that has already loaded, so there is no race
      // between attaching the handler and the request finishing.
      var component = this.getOwnerComponent();
      var models = ["programmeBurn", "closeMonitor", "varianceByPeriod"];

      Promise.all(
        models.map(function (name) { return component.getModel(name).dataLoaded(); })
      ).then(this._styleCharts.bind(this));
    },

    _styleCharts: function () {
      var view = this.getView();

      var burn = view.byId("burnChart");
      if (burn) {
        burn.setVizProperties({
          title: { visible: false },
          legend: { visible: true },
          plotArea: {
            dataLabel: { visible: false },
            bubbleSizeMax: 42,
            bubbleSizeMin: 8,
            referenceLine: {
              line: {
                valueAxis2: [{
                  value: 0,
                  visible: true,
                  size: 2,
                  type: "dotted",
                  label: { text: "On plan", visible: true }
                }]
              }
            }
          },
          valueAxis: {
            title: { visible: true, text: "Share of schedule elapsed" },
            label: { formatString: "0%" },
            axisLine: { visible: true }
          },
          // Deviation from plan, so zero is "on plan" and the reference line
          // below is the whole reading of the chart.
          //
          // The first version plotted budget-consumed here and asked the
          // reader to judge against a 45-degree diagonal. That only works if
          // both axes share a range, and VizFrame rescales on data binding -
          // it produced a 0-120% x-axis against a 0-150% y-axis, so the
          // diagonal on screen was not the diagonal in the subtitle. Two
          // attempts to pin the ranges were overwritten by the framework.
          // Plotting the deviation removes the dependency instead of fighting
          // it: a horizontal line at zero cannot be rescaled into a lie.
          valueAxis2: {
            title: { visible: true, text: "Burning faster than schedule" },
            label: { formatString: "0%" }
          },
          // Without this the size legend prints raw euros - "690,327,297.27"
          // as a legend entry, which is noise where a scale was wanted.
          sizeLegend: {
            title: { visible: true, text: "Programme budget" },
            formatString: "#,##0,, M"
          },
          tooltip: { visible: true },
          interaction: { selectability: { mode: "single" } }
        });
      }

      var close = view.byId("closeChart");
      if (close) {
        close.setVizProperties({
          title: { visible: false },
          legend: { visible: true },
          valueAxis: {
            title: { visible: true, text: "Working days after period end" }
          },
          categoryAxis: {
            title: { visible: false },
            label: { angle: 45 }
          },
          plotArea: {
            dataLabel: { visible: false },
            // Working day 5 is the group target. A reference line turns the
            // chart from "these are the numbers" into "these are the misses".
            referenceLine: {
              line: {
                valueAxis: [{
                  value: 5,
                  visible: true,
                  size: 2,
                  type: "dotted",
                  label: { text: "Target: WD 5", visible: true }
                }]
              }
            }
          }
        });
      }

      var variance = view.byId("varianceChart");
      if (variance) {
        variance.setVizProperties({
          title: { visible: false },
          legend: { visible: true },
          valueAxis: {
            title: { visible: true, text: "EUR" },
            label: { formatString: "#,##0,, M" }
          },
          categoryAxis: { title: { visible: false }, label: { angle: 45 } },
          plotArea: { dataLabel: { visible: false } }
        });
      }
    },

    // -- formatters ---------------------------------------------------------

    formatPercent: function (value) {
      if (value === null || value === undefined) { return ""; }
      return (value * 100).toFixed(1) + " %";
    },

    formatMillions: function (value) {
      if (value === null || value === undefined) { return ""; }
      return (value / 1000000).toFixed(1) + " M";
    },

    formatEuro: function (value) {
      if (value === null || value === undefined) { return ""; }
      return value.toLocaleString("en-GB", {
        minimumFractionDigits: 2, maximumFractionDigits: 2
      });
    },

    /**
     * Criticality comes from the database, not from the UI: the thresholds live
     * in NOVASPACE_API so every client colours identically. 0 means "no value",
     * which is deliberately not the same as "good".
     */
    formatCriticality: function (criticality) {
      switch (criticality) {
        case 1:  return ValueState.Error;
        case 2:  return ValueState.Warning;
        case 3:  return ValueState.Success;
        default: return ValueState.None;
      }
    },

    formatCloseState: function (days) {
      if (days === null || days === undefined) { return ValueState.None; }
      if (days > 7) { return ValueState.Error; }
      if (days > 5) { return ValueState.Warning; }
      return ValueState.Success;
    }
  });
});
