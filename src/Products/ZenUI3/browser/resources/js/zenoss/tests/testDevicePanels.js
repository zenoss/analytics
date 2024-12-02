/** global describe:true, it:true, expect:true, **/
window.describe("DevicePanels", function() {

  window.it("should be able to be created ", function() {
      var panel = Ext.create("Zenoss.DeviceGridPanel", {});
      window.expect(panel.id).toEqual(panel.id);
  });

});
