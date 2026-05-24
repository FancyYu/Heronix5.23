// pages/simplify/simplify.js
Page({
  data: {
    inputText: '',
    outputText: ''
  },

  onInput: function(e) {
    this.setData({ inputText: e.detail.value });
  },

  simplify: function() {
    var text = this.data.inputText.trim();
    if (!text) return;

    var result = text
      .replace(/因此|所以|故而|由此可见/g, '所以')
      .replace(/然而|但是|不过|尽管如此/g, '但是')
      .replace(/此外|另外|除此之外|与此同时/g, '还有')
      .replace(/鉴于|考虑到|基于上述原因/g, '因为')
      .replace(/实施|执行|落实|推进/g, '做')
      .replace(/进行|开展|予以/g, '')
      .replace(/具有|具备|拥有/g, '有')
      .replace(/利用|运用|采用/g, '用')
      .replace(/确保|保证|保障/g, '让')
      .replace(/应当|应该|必须|务必/g, '要')
      .replace(/能够|可以|得以/g, '能')
      .trim();

    this.setData({ outputText: result || text });
  },

  copyResult: function() {
    wx.setClipboardData({
      data: this.data.outputText,
      success: function() {
        wx.showToast({ title: '已复制', icon: 'success' });
      }
    });
  },

  clearAll: function() {
    this.setData({ inputText: '', outputText: '' });
  }
});
