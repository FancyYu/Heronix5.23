// pages/focus/focus.js
Page({
  data: {
    displayTime: '25:00',
    timerLabel: '准备开始',
    btnText: '开始专注',
    presets: [
      { min: 25, active: true },
      { min: 15, active: false },
      { min: 10, active: false },
      { min: 5, active: false },
      { min: 45, active: false }
    ]
  },

  _timerInterval: null,
  _totalSeconds: 25 * 60,
  _remainSeconds: 25 * 60,
  _running: false,
  _ctx: null,
  _canvasSize: 280,

  onReady: function() {
    this._drawCanvas(1);
  },

  _drawCanvas: function(ratio) {
    var self = this;
    var query = wx.createSelectorQuery();
    query.select('#timerCanvas').fields({ node: true, size: true }).exec(function(res) {
      if (!res || !res[0]) return;
      var canvas = res[0].node;
      var size = res[0].width || 280;
      var dpr = wx.getWindowInfo ? wx.getWindowInfo().pixelRatio : 2;
      canvas.width = size * dpr;
      canvas.height = size * dpr;
      var ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
      self._ctx = ctx;
      self._canvasSize = size;
      self._renderCircle(ratio);
    });
  },

  _renderCircle: function(ratio) {
    var ctx = this._ctx;
    if (!ctx) return;
    var size = this._canvasSize;
    var cx = size / 2, cy = size / 2, r = size / 2 - 12;
    ctx.clearRect(0, 0, size, size);

    // Track
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = '#C4D8ED';
    ctx.lineWidth = 8;
    ctx.stroke();

    // Progress
    if (ratio > 0) {
      ctx.beginPath();
      ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * ratio);
      ctx.strokeStyle = this._running ? '#8CAFD4' : '#D4A88C';
      ctx.lineWidth = 8;
      ctx.lineCap = 'round';
      ctx.stroke();
    }
  },

  toggleTimer: function() {
    if (this._running) {
      clearInterval(this._timerInterval);
      this._running = false;
      this.setData({ btnText: '继续', timerLabel: '已暂停' });
    } else {
      this._running = true;
      this.setData({ btnText: '暂停', timerLabel: '专注中...' });
      var self = this;
      this._timerInterval = setInterval(function() {
        if (self._remainSeconds <= 0) {
          clearInterval(self._timerInterval);
          self._running = false;
          self.setData({ btnText: '重新开始', timerLabel: '🎉 完成！休息一下', displayTime: '00:00' });
          self._renderCircle(0);
          wx.vibrateShort({ type: 'medium' });
          return;
        }
        self._remainSeconds--;
        var ratio = self._remainSeconds / self._totalSeconds;
        var m = Math.floor(self._remainSeconds / 60).toString().padStart(2, '0');
        var s = (self._remainSeconds % 60).toString().padStart(2, '0');
        self.setData({ displayTime: m + ':' + s });
        self._renderCircle(ratio);
      }, 1000);
    }
  },

  resetTimer: function() {
    clearInterval(this._timerInterval);
    this._running = false;
    this._remainSeconds = this._totalSeconds;
    var m = Math.floor(this._totalSeconds / 60).toString().padStart(2, '0');
    this.setData({ displayTime: m + ':00', timerLabel: '准备开始', btnText: '开始专注' });
    this._renderCircle(1);
  },

  setTimer: function(e) {
    var min = e.currentTarget.dataset.min;
    var idx = e.currentTarget.dataset.index;
    clearInterval(this._timerInterval);
    this._running = false;
    this._totalSeconds = min * 60;
    this._remainSeconds = min * 60;
    var presets = this.data.presets.map(function(p, i) { return { min: p.min, active: i === idx }; });
    this.setData({
      presets: presets,
      displayTime: min.toString().padStart(2, '0') + ':00',
      timerLabel: '准备开始',
      btnText: '开始专注'
    });
    this._renderCircle(1);
  },

  noop: function() {},

  onUnload: function() {
    clearInterval(this._timerInterval);
  }
});
