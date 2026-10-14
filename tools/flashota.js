// OTA transport for flashota.py: sends 55 AA frames over StarFun's own authenticated SPP
// socket (message type 3, same as the app's OTA path) and forwards replies and link events.
'use strict';

Java.perform(function () {
  var BtClient = Java.use('com.sjbt.base.bt.BtClient');
  var BtBase = Java.use('com.sjbt.base.bt.BtBase');

  var client = BtClient.getInstance(null);
  send({ t: 'log', m: 'client connected=' + client.isConnected(null) });

  // 0 = link lost, 1 = connected, 2 = inbound frame (hex string)
  BtBase.notifyUI.implementation = function (i, obj) {
    if (i === 0) {
      send({ t: 'disc' });
    } else if (i === 1) {
      send({ t: 'conn' });
    } else if (i === 2) {
      var s = null;
      try { s = obj ? obj.toString() : null; } catch (e) {}
      if (s && /^55AA/i.test(s)) send({ t: 'rx', hex: s });
    }
    return this.notifyUI(i, obj);
  };

  rpc.exports = {
    ota: function (hex) {
      var b = [];
      for (var k = 0; k < hex.length; k += 2) {
        var v = parseInt(hex.substr(k, 2), 16);
        b.push(v > 127 ? v - 256 : v);
      }
      Java.perform(function () {
        client.sendBytes(Java.array('byte', b), 3);
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
