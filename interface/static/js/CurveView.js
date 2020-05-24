var CurveView = Backbone.View.extend({
    tagName: 'div',
    className: 'curve-view',

    events: {},

    initialize: function(options) {
        options = options || {};
        _.bindAll(this, 'updateLoop', 'onFuncChanged');

        this.$container = options.$container;
        this.paused = false;

        this.curveFuncs = options.curveFuncs;
        this.curveFuncs.on('FuncChanged', this.onFuncChanged)

        var size = this.getSize();

        this.width = size.w;
        this.height = size.h;

        this.$el.css({
            'position': 'absolute',
            'width': '100%',
            'height': '100%',
            'overflow': 'hidden'
        });

        this.$period = $('<div>')
                            .attr('id', 'curve-period')
                            .addClass('curve-period')
                            .css({
                                'position': 'absolute',
                                'textAlign': 'center',
                                'bottom': '5%',
                                'left': '30%',
                                'width': '40%',
                                'height': '5%',
                                'zIndex': 5,
                                'color': 'orange'
                            })
                            .appendTo(this.$el);

        this.initialX = 0;

        this.segments = [];
        this.initSegment(this.initialX);
        this.initSegment(this.initialX);
        
        this.stepsPerPeriod = 22;
        this.minXStep = 5;
        this.xStep = 3;
        this.shiftStep = 1;

        this.displayInterval = options.displayInterval || 1200;
        this.displayIntervalAnchor = options.displayIntervalAnchor || Date.now();

        this.lastBackgroundState = null;
        this.currentX = this.initialX;

        this.leftSegmentPos = 0;
        this.rightSegmentPos = 1;

        this.intervalCtr = 0;

        this.updateFrequency = 30;

        this.updateInterval(options.intervalLength);
    },

    updateInterval: function(intervalLength) {
        this.intervalLength = intervalLength;

        var msPerPixel = this.width / intervalLength,
            pixelsPerUpdate = msPerPixel * (1000 / this.updateFrequency);

        this.shiftStep = pixelsPerUpdate;
        this.timeStep = intervalLength / (this.width / this.xStep);
    },

    updatePeriod: function(x) {
        this.$period.html(x + 's');
    },

    onFuncChanged: function(waveDef) {
        if (waveDef) {
            this.updateInterval(waveDef.period * 1000 * 15);
            this.updatePeriod(parseInt(Math.round(waveDef.period)))
        }

        this.intervalCtr = 0;

        this.anchorTime = Date.now(); // May be any time
        this.refTime = Date.now(); // Always now
        this.backgroundTimeAdjust = this.anchorTime % this.displayInterval;

        this.currentX = this.initialX;
        this.positionSegment(0, this.currentX, 0);
        this.positionSegment(1, this.currentX, 1);

        this.renderSegment(this.leftSegmentPos, true, 0);
        this.renderSegment(this.rightSegmentPos, true, 1);

        this.beginUpdateLoop();
    },

    initSegment: function(initialX) {
        var canvas = this.initCanvas(this.initialX);
        this.$el.append(canvas);
        this.segments.push([canvas.getContext('2d'), $(canvas), canvas]);
    },

    initCanvas: function(initialX) {
        var canvas = document.createElement('canvas');
        
        canvas.width = this.width;
        canvas.height = this.height;
        
        context = canvas.getContext('2d');
        context.strokeStyle = '#222';
        context.lineJoin = 'round';
        context.save();

        $(canvas)
            .css({
                'position': 'absolute',
                'transform': 'translateX(' + initialX + 'px)'
            });

        return canvas;
    },

    getSize: function() {
        return {
            w: this.$container.width(),
            h: this.$container.height()
        }
    },

    render: function(options) {
        options = options || {};

        this.anchorTime = Date.now(); // May be any time
        this.refTime = Date.now(); // Always now
        this.backgroundTimeAdjust = this.anchorTime % this.displayInterval;

        /*_.each(this.segments, function(segment, segmentIdx) {
            // Set initial position
            this.positionSegment(segmentIdx, 0, segmentIdx);

            this.renderSegment(segmentIdx, true, true);
        }, this);*/

        this.positionSegment(0, 0, 0);
        this.renderSegment(0, true);

        if (!options.noUpdate) {
            this.beginUpdateLoop();
        }
        return this;
    },

    beginUpdateLoop: function(force) {
        if (!this.updating || force) {
            this.updating = true;
            this.updateLoop();
        }
    },

    updateLoop: function() {
        this.positionSegment(0, this.currentX, this.leftSegmentPos);
        this.positionSegment(1, this.currentX, this.rightSegmentPos);

        if (this.currentX < -this.width) {
            // Swap
            this.leftSegmentPos = this.rightSegmentPos;
            this.rightSegmentPos = this.leftSegmentPos == 1 ? 0 : 1;

            this.currentX = this.initialX;
        }
        else {
            // Render right-side, with time offset
            if (this.currentX == this.initialX) {
                this.intervalCtr += 1;
                this.renderSegment(this.rightSegmentPos, true, this.intervalCtr);
            }
            this.currentX -= this.shiftStep;
        }

        setTimeout(this.updateLoop, 1000 / this.updateFrequency);
    },

    renderSegment: function(segmentIdx, useLastBackgroundState, intervalOffset) {
        var ctx = this.segments[segmentIdx][0];
        //this.renderBackground(ctx, null, useLastBackgroundState);

        ctx.beginPath();
        ctx.rect(0, 0, this.width, this.height);
        ctx.fillStyle = '#000';
        ctx.fill();

        _.each(this.curveFuncs.getFuncs(), function(funcDef) {
            this.renderCurve(ctx, funcDef, intervalOffset || 0);
        }, this);
    },

    renderBackground: function(ctx, beginPos, useLastState) {
        beginPos = beginPos || 0;

        var onEven = true;

        var intervalWidth = (this.displayInterval / this.intervalLength) * this.width,
            n = Math.ceil(this.intervalLength / this.displayInterval);

        if (useLastState && this.lastBackgroundState) {
            onEven = this.lastBackgroundState.onEven;
            beginPos = this.lastBackgroundState.endOverlap - intervalWidth;
        }

        var pos = beginPos,
            intervalIdx = 0;

        n += Math.abs(Math.ceil(pos / intervalWidth)) + 1;

        _.each(_.range(0, n), function(intervalIdx) {
            ctx.beginPath();
            ctx.rect(pos, 0, intervalWidth, this.height);
            ctx.fillStyle = onEven ? '#111' : '#000';
            ctx.fill();

            ctx.fillStyle = '#444';
            ctx.font = Math.min(this.height * 0.1, (intervalWidth * 0.2)) + 'px sans-serif';
            ctx.textBaseline = 'bottom';
            ctx.textAlign = 'center';

            var intervalTime = (this.anchorTime - this.backgroundTimeAdjust) + (intervalIdx * this.displayInterval * 1);
            var label = moment(intervalTime).format('mm:ss');
            ctx.fillText(label, pos + (intervalWidth / 2), this.height);

            pos += intervalWidth;
            onEven = !onEven;
        }, this);

        this.lastBackgroundState = {
            'endOverlap': (pos - intervalWidth) - this.width,
            'beginPos': beginPos,
            'onEven': onEven
        }
    },

    renderCurve: function(ctx, funcDef, intervalOffset) {
        var f = funcDef.func;

        ctx.strokeStyle = funcDef.color || '#00f';
        ctx.lineWidth = funcDef.size || 2;
        ctx.beginPath();

        var anchorTime = this.anchorTime,
            deltaTime = 0,
            height = this.height,
            width = this.width,
            timeStep = this.timeStep,
            xStep = this.xStep,
            x = 0,
            y, decay, graphHeight, centerAdjust, rawHeight, decayedHeight, decayDelta;

        if (intervalOffset) {
            anchorTime += intervalOffset * this.intervalLength;
        }

        var centerAxis = height / 2

        var result = f(anchorTime);
        y = (result.y * result.decay)
        ctx.moveTo(0, (y * height) + ((height - (height * result.decay)) / 2));

        for (i = 0; i <= width + xStep; i += xStep) {
            deltaTime += timeStep;
            result = f(anchorTime + deltaTime);
            y = result.y * result.decay;
            ctx.lineTo(i, (y * height) + ((height - (height * result.decay)) / 2));
        }

        ctx.stroke();
    },

    positionSegment: function(segmentIdx, x, pos) {
        x = x || 0;
        x += (pos * this.width);

        var $canvas = this.segments[segmentIdx][1];
        $canvas.css({
            'transform': 'translateX(' + x + 'px)'
        });
    }
});
