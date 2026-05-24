/**
 * MindBloom · 小程序 API 工具
 * 对接 MindBloom Agent 服务（默认 localhost:8080）
 */

const AGENT_API = 'http://localhost:8080';  // 部署时替换为实际 IP
const DEFAULT_USER_ID = 'demo_user_001';

// 本地兜底回复（Agent 不可用时）
const FALLBACK_REPLIES = {
  '无聊': '听起来你现在可能有点不知道做什么好 🌿\n\n要不要试试这几件小事？\n• 听一首你很久没听的歌\n• 画一张随手涂鸦（不需要好看）\n• 看一个 3 分钟的趣味科普视频\n\n选一个最没压力的试试看？',
  '动不了': '启动确实是最难的一步 💪\n\n试试这个：\n1. 倒数 5-4-3-2-1\n2. 然后只做 2 分钟\n3. 2 分钟后可以停\n\n你现在能做的第一个最小动作是什么？',
  '分心': '注意力被拉走很正常的 🌿\n\n先试试：\n• 设置 5 分钟倒计时\n• 这 5 分钟只做一件事\n• 时间到了就站起来活动一下\n\n要不要先设定一个 5 分钟的番茄钟？',
  'default': '谢谢你愿意跟我说这些 💚\n\n你的感受是有效的。有什么想聊聊的吗？'
};

function getFallback(input) {
  var lower = input.toLowerCase();
  for (var key in FALLBACK_REPLIES) {
    if (lower.includes(key)) return FALLBACK_REPLIES[key];
  }
  return FALLBACK_REPLIES['default'];
}

/**
 * 调用 MindBloom Agent
 * @param {string} userMsg - 用户消息
 * @param {string} userId - 用户 ID（可选）
 * @returns {Promise<{reply: string}>}
 */
function callAI(userMsg, userId) {
  return new Promise(function(resolve) {
    wx.request({
      url: AGENT_API + '/chat',
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: {
        user_id: userId || DEFAULT_USER_ID,
        message: userMsg
      },
      success: function(res) {
        if (res.statusCode === 200 && res.data && res.data.reply) {
          resolve({ reply: res.data.reply });
        } else {
          console.error('Agent error:', res);
          resolve({ reply: getFallback(userMsg) });
        }
      },
      fail: function(err) {
        console.error('Agent request failed:', err);
        resolve({ reply: getFallback(userMsg) });
      }
    });
  });
}

module.exports = {
  callAI: callAI,
  getFallback: getFallback
};