// Read flash off the buds through StarFun's own authenticated SPP socket.
// Read-only: only C0 83 (flash read) frames are ever sent.
'use strict';

var ADDR = parseInt(get_env('DUMP_ADDR', '0x3000'), 16);
var LEN = parseInt(get_env('DUMP_LEN', '200'), 10);
var CHUNK = parseInt(get_env('DUMP_CHUNK', '100'), 10);

function get_env(k, d) {
  try { return (typeof CONF !== 'undefined' && CONF[k]) ? CONF[k] : d; } catch (e) { return d; }
}

Java.perform(function () {
  var BtClient = Java.use('com.sjbt.base.bt.BtClient');
  var BtBase = Java.use('com.sjbt.base.bt.BtBase');
  var CMDConfig = Java.use('com.sjbt.base.bt.CMDConfig');

  var client = BtClient.getInstance(null);
  send({ t: 'log', m: 'client connected=' + client.isConnected(null) });

  // capture every inbound frame
  BtBase.notifyUI.implementation = function (i, obj) {
    if (i === 2) {
      var s = null;
      try { s = obj ? obj.toString() : null; } catch (e) {}
      if (s && /^C083/i.test(s)) send({ t: 'rx', hex: s });
    }
    return this.notifyUI(i, obj);
  };

  rpc.exports = {
    read: function (addr, len) {
      Java.perform(function () {
        var cmd = CMDConfig.getReadFlashCmdArray(addr, len);
        client.sendBytes(cmd, 1);
      });
      return true;
    },
    connected: function () {
      var r = false;
      Java.perform(function () { r = client.isConnected(null); });
      return r;
    }
  };
  send({ t: 'ready' });
});
