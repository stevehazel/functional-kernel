var ButtonView = Backbone.View.extend({
    tagName: 'div',
    className: 'button-view',

    events: {
        'click': 'addPoint'
    },

    initialize: function(options) {
        options = options || {};
        _.bindAll(this, 'addPoint');

        this.$container = options.$container;
        this.sessionID = options.sessionID;
        this.nodeUUID = options.nodeUUID;
        this.onAddPoint = options.onAddPoint;

        this.label = options.label;

        this.buttonID = '' + parseInt(Math.random() * 10000000);

        this.utils = new Utils();

        this.minIntervals = options.minIntervals || 2;
        this.maxIntervals = options.maxIntervals || 5;

        this.isMobile = ('ontouchstart' in document.documentElement);
        if ('webkitAnimation' in document.body.style) {
            this.cssPrefix = '-webkit-';
        }
        else if ('MozAnimation' in document.body.style) {
            this.cssPrefix = '-moz-';
        }

        var _this = this;
        if (this.isMobile) {
            this.$el
                .on('touchstart', function() { $(this).addClass('touchactive') })
                .on('touchend', function() { $(this).removeClass('touchactive') });
        }
        else {
            this.$el
                .on('mousedown', function() {
                    $(this).addClass('touchactive');
                    _this.renderInsetColor();
                })
                .on('mouseup', function() {
                    $(this).removeClass('touchactive');
                    _this.renderColor();
                });
        }
    },

    render: function() {
        if (!this.$label) {
            var size = this.getSize();
            this.$label = $('<div>')
                                .addClass('label')
                                .css({
                                    'font-size': (((size.h + size.w) / 2) * 0.1) + 'px'
                                })
                                .appendTo(this.$el);
        }

        if (this.label) {
            this.setLabel(this.label);
        }

        this.renderColor();

        return this;
    },

    renderColor: function(baseColor) {
        baseColor = baseColor || this.utils.getColor(this.nodeUUID);

        var c = $.Color(baseColor),
            darkColor = $.Color()
                                .lightness(c.lightness() * 0.7)
                                .saturation(c.saturation() * 1.3)
                                .hue(c.hue());

        this.applyColor(c, darkColor);
    },

    renderInsetColor: function(baseColor) {
        baseColor = baseColor || this.utils.getColor(this.nodeUUID);

        var c = $.Color(baseColor),
            darkColor0 = $.Color()
                                .lightness(c.lightness() * 0.92)
                                .saturation(c.saturation() * 1.0)
                                .hue(c.hue()),
            darkColor2 = $.Color()
                                .lightness(c.lightness() * 0.6)
                                .saturation(c.saturation() * 1.6)
                                .hue(c.hue());

        this.applyColor(darkColor0, darkColor2);
    },

    applyColor: function(c1, c2, pos) {
        var first = c1.toRgbaString(),
            second = c2.toRgbaString(),
            pos = pos || 0.775;

        this.$el.css({
            'background': this.utils.getRadialGradient([first, second], [0, pos, 1.0], first)
        });
    },

    getSize: function() {
        return {
            w: this.$el.width(),
            h: this.$el.height(),
        }
    },

    setLabel: function(label) {
        this.$label.text(label);
    },

    addPoint: function() {
        var pointTime = Date.now();
        this.onAddPoint(this.sessionID, this.nodeUUID, pointTime)
    }
});