function setupSocket(namespace, resourceName, listeners) {
    namespace = namespace || '';
    var socket = io('//' + document.domain + ':' + location.port + namespace,
            {
                path : resourceName,
                'force new connection': true
            });

    _.each(listeners, function(func, eventName) {
        socket.on(eventName, func);
    });

    return socket;
}

$(document).ready(function() {
    var sessionID = window.SESSION_ID,
        nodeUUID = window.NODE_UUID;

    var socket = setupSocket('/signals', '/signal_socket', {
        connect: function() {
            // Immediately verify the connection
            this.emit('event', {
                msg: 'SignalConnectionInit',
                data: {
                    session_id: sessionID,
                    node_uuid: nodeUUID
                }
            });
        },
        control: function(msg) {
            if (msg.Msg == 'SignalConnectionInit') {
                console.log('Signal socket verified');
                if (msg.Signal) {
                    waveState.onNewSignal(msg.Signal)
                }
            }
        }
    });

    function onAddPoint(sessionID, nodeUUID, pointTime) {
        socket.emit('event', {
            msg: 'AddPoint',
            data: {
                'session_id': sessionID,
                'node_uuid': nodeUUID,
                'point_time': pointTime
            }
        });
    }

    var globalWidth = $(window).width(),
        globalHeight = $(window).height(),
        refSize = (globalWidth + globalHeight) / 2,
        buttonRadius = 0.2 * refSize,

        buttonAreaTop = (globalHeight - buttonRadius) / 2,
        buttonAreaLeft = (globalWidth - buttonRadius) / 2;

    var $container = $('<div>')
                            .attr('id', 'button-container')
                            .addClass('button-container')
                            .css({
                                'top': buttonAreaTop + 'px',
                                'left': buttonAreaLeft + 'px',
                                'width': buttonRadius + 'px',
                                'height': buttonRadius + 'px'
                            })
                            .appendTo($('body'));

    var button = new ButtonView({
        $container: $container, 
        sessionID: sessionID,
        nodeUUID: nodeUUID,
        onAddPoint: onAddPoint,
        minIntervals: 1,
        maxIntervals: 3,
        label: ''
    });
    button.$el.appendTo($container);
    button.render();

    var $curveContainer = $('#curve-container').css({borderTop: '2px solid #111', borderBottom: '2px solid #111'});

    var waveState = new WaveState({});
    socket.on('signal', waveState.onNewSignal);

    var curve = new CurveView({
        activityID: nodeUUID,
        $container: $curveContainer, 
        displayInterval: 1000,
        displayIntervalAnchor: Date.now(),
        intervalLength: 2000,
        curveFuncs: waveState
    });
    curve.$el.appendTo($curveContainer);
});
