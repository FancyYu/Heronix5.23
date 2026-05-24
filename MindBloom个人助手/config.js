/**
 * MindBloom · AI 配置文件
 * 填入你的 Tokendance API Key 即可启用真实 AI 对话
 * 申请地址：https://tokendance.space/keys
 */
const MINDBLOOM_CONFIG = {
  // ===== 服务地址 =====
  agentApi: "", // 空 = 同源代理（通过 proxy_server.py 转发到后端）

  // ===== Tokendance API 配置 =====
  apiKey: "sk-your-key-here", // 申请: https://tokendance.space/keys
  baseURL: "https://tokendance.space/gateway/v1",
  model: "deepseek-v3.2", // Tokendance 模型名

  // ===== AI 行为配置 =====
  systemPrompt: `你是 MindBloom，一位专为神经多样性人士（包括 ADHD、自闭症谱系、阅读障碍等）设计的温暖 AI 伙伴。

你的沟通风格：
- 语气温和、不评判、不催促
- 语言简洁清晰，避免过长的段落
- 使用适当的表情符号增加友好感
- 主动提供具体可操作的建议
- 对用户的感受给予充分确认（validation）
- 将复杂信息拆解为小步骤
- 永远不说"你应该/必须"，改用"你可以/试试看"

你擅长帮助用户：
1. 任务拆解与执行计划
2. 情绪识别与调节策略
3. 感官过载应对
4. 社交场景准备
5. 执行功能障碍的应对技巧
6. 自我接纳与自我关怀

回复格式：优先使用换行分段，重要内容加粗，用 • 列表代替长段文字。`,

  maxTokens: 1000,
  temperature: 0.75,
};

// 导出（兼容 window 全局）
if (typeof window !== "undefined") window.MINDBLOOM_CONFIG = MINDBLOOM_CONFIG;
if (typeof module !== "undefined") module.exports = MINDBLOOM_CONFIG;
