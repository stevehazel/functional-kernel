function WaveState(options) {
    options = options || {};
    _.bindAll(this, 'onNewSignal');

    this.waveFunc = null;
    this.refTime = Date.now() - 0;
}
_.extend(WaveState.prototype, Backbone.Events);
_.extend(WaveState.prototype, {
    onNewSignal: function(signalDef) {
        if (signalDef.action == 'Delete') {
            this.waveFunc = null
        }
        else if (signalDef.action == 'Update') {
            this.waveFunc = signalDef.data
        }

        if (signalDef.action == 'Delete' || signalDef.action == 'Update') {
            this.trigger('FuncChanged', this.waveFunc);
        }
    },

    getFuncs: function() {
        var _this = this;

        return [
            {
                size: 2,
                color: '#00f',
                func: function(t) {
                    return _this.sin(t, _this.waveFunc);
                    
                }
            }
        ]
    },

    sin: function(t, waveDef) {
        var period = waveDef.period * 1000 * 2,
            decay = waveDef.decay || 0,
            waveRefTime = waveDef.ref_time * 1000,

            projection = t - waveRefTime,
            x = projection / period,
            d = Math.pow(Math.E, -decay * x),
            y = Math.cos(x * (2 * Math.PI));

        var posY = ((y + 1) / 2),
            decayDiff = posY - (d * posY),
            val = posY - decayDiff;

        return {
            y: posY,
            decay: d
        }
    }
});