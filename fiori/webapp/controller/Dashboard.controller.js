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
      this.getView().loaded().then(this._styleCharts.bind(this));
    },

    _styleCharts: function () {
      var view = this.getView();

      var burn = view.byId("burnChart");
      if (burn) {
        burn.setVizProperties({
          title: { visible: false },
          legend: { visible: true },
          plotArea: {
            // Both axes are shares of a whole, so both are fixed to 0-100%.
            // Letting them auto-scale would hide the diagonal relationship
            // that the entire chart exists to show.
            dataLabel: { visible: false },
            bubbleSizeMax: 42,
            bubbleSizeMin: 8
          },
          valueAxis: {
            title: { visible: true, text: "Share of schedule elapsed" },
            label: { formatString: "0%" },
            axisLine: { visible: true }
          },
          valueAxis2: {
            title: { visible: true, text: "Share of budget consumed" },
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
