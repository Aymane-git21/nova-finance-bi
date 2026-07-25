sap.ui.define([
  "sap/ui/core/UIComponent",
  "sap/ui/model/json/JSONModel"
], function (UIComponent, JSONModel) {
  "use strict";

  return UIComponent.extend("novaspace.cockpit.Component", {

    metadata: { manifest: "json" },

    init: function () {
      UIComponent.prototype.init.apply(this, arguments);

      // Each dataset is a frozen snapshot of one OData response. Named models
      // rather than one merged blob, so the mapping back to the service entity
      // it came from stays obvious.
      [
        "kpi", "programmeBurn", "closeMonitor", "entitySummary",
        "varianceByPeriod", "varianceByProgramme", "icOpenItems"
      ].forEach(function (name) {
        this.setModel(
          new JSONModel(sap.ui.require.toUrl("novaspace/cockpit/localData/" + name + ".json")),
          name
        );
      }, this);
    }
  });
});
