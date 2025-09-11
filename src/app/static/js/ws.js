/**
 * Socket.IO client for realtime progress updates.
 * Server namespace: /progress (see src/app/sockets.py)
 */
(function () {
  let socket = null;
  const listeners = new Set();

  function connect() {
    if (socket) return socket;
    try {
      // Connect to the progress namespace
      socket = io("/progress", {
        transports: ["websocket", "polling"],
        forceNew: true,
      });

      // Forward all known events to listeners
      const forward = (type) => (payload) => {
        for (const cb of listeners) {
          try {
            cb({ type, payload });
          } catch (e) {
            console.error("WS listener error:", e);
          }
        }
      };

      socket.on("connect", () => forward("connected")({}));
      socket.on("disconnect", () => forward("disconnected")({}));

      socket.on("job.queued", forward("job.queued"));
      socket.on("analyzer.started", forward("analyzer.started"));
      socket.on("analyzer.completed", forward("analyzer.completed"));
      socket.on("stage.completed", forward("stage.completed"));
      socket.on("job.completed", forward("job.completed"));
      socket.on("job.error", forward("job.error"));
      // Insights updates
      socket.on("insights.updated", forward("insights.updated"));
      
      // Log events
      socket.on("log.debug", forward("log.debug"));
      socket.on("log.info", forward("log.info"));
      socket.on("log.warning", forward("log.warning"));
      socket.on("log.error", forward("log.error"));
    } catch (e) {
      console.error("Socket connect error:", e);
    }
    return socket;
  }

  function onEvent(cb) {
    listeners.add(cb);
    // Lazy connect on first subscription
    if (!socket) connect();
    return () => listeners.delete(cb);
  }

  function disconnect() {
    if (socket) {
      try {
        socket.disconnect();
      } catch (e) {
        // ignore
      }
      socket = null;
    }
    listeners.clear();
  }

  window.WS = {
    connect,
    onEvent,
    disconnect,
  };
})();
