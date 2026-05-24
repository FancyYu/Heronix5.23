// pages/chat/chat.js
var api = require('../../utils/api');

Page({
  data: {
    messages: [
      {
        id: 0,
        role: 'ai',
        content: '嗨 👋 我是 MindBloom，你的AI伙伴。\n\n你可以跟我聊任何事——无论是需要拆解一个任务、处理情绪，还是只是想有人陪着说说话。这里没有对错，按你的方式来就好。'
      }
    ],
    inputText: '',
    loading: false,
    scrollTo: '',
    isOnline: !!(api.CONFIG.apiKey && api.CONFIG.apiKey.trim()),
    quickTopics: [
      { label: '😵‍💫 感觉超负荷', text: '我今天感觉有点 overwhelmed' },
      { label: '📅 制定计划', text: '帮我制定一个今天的计划' },
      { label: '🤝 社交建议', text: '我需要社交场景的应对建议' },
      { label: '🧠 执行功能障碍', text: '解释一下 executive dysfunction' },
      { label: '💛 自我关怀', text: '给我一些自我关怀的小建议' }
    ],
    chatHistory: []
  },

  onInput: function(e) {
    this.setData({ inputText: e.detail.value });
  },

  sendQuick: function(e) {
    var text = e.currentTarget.dataset.text;
    this.setData({ inputText: text });
    this.sendMessage();
  },

  sendMessage: function() {
    var text = this.data.inputText.trim();
    if (!text || this.data.loading) return;

    var msgs = this.data.messages;
    var history = this.data.chatHistory;
    var id = msgs.length;

    msgs.push({ id: id, role: 'user', content: text });
    this.setData({
      messages: msgs,
      inputText: '',
      loading: true,
      scrollTo: 'msg' + id
    });

    var self = this;
    api.callAI(text, history).then(function(result) {
      var newMsgs = self.data.messages;
      var newId = newMsgs.length;
      newMsgs.push({ id: newId, role: 'ai', content: result.reply });

      var newHistory = history.concat([
        { role: 'user', content: text },
        { role: 'assistant', content: result.reply }
      ]);
      // 保留最近 20 条
      if (newHistory.length > 20) newHistory = newHistory.slice(-20);

      self.setData({
        messages: newMsgs,
        loading: false,
        chatHistory: newHistory,
        scrollTo: 'msg' + newId
      });
    });
  }
});
