// pages/tasks/tasks.js
var TASK_TEMPLATES = {
  '演讲': [
    { text: '确定演讲的核心主题（1个关键信息）', time: '10 min' },
    { text: '列出3个支撑要点', time: '15 min' },
    { text: '为每个要点找1个例子或故事', time: '20 min' },
    { text: '写开头（吸引注意力的方式）', time: '15 min' },
    { text: '写结尾（总结+行动号召）', time: '10 min' },
    { text: '制作幻灯片草稿', time: '30 min' },
    { text: '自己练习讲一遍（计时）', time: '20 min' },
    { text: '修改不满意的部分', time: '15 min' }
  ],
  '整理': [
    { text: '设定计时器 10 分钟', time: '1 min' },
    { text: '只处理一个区域', time: '10 min' },
    { text: '准备三个袋子：保留/丢弃/待定', time: '5 min' },
    { text: '快速分类物品', time: '10 min' },
    { text: '休息 5 分钟', time: '5 min' },
    { text: '继续下一个小区域', time: '10 min' },
    { text: '处理"丢弃"袋', time: '5 min' },
    { text: '肯定自己：我做到了！', time: '1 min' }
  ],
  '报告': [
    { text: '明确报告的目的和读者', time: '10 min' },
    { text: '列出大纲标题', time: '15 min' },
    { text: '收集数据和资料', time: '30 min' },
    { text: '先写最容易的部分', time: '25 min' },
    { text: '休息', time: '5 min' },
    { text: '补充剩余章节', time: '30 min' },
    { text: '写摘要和结论', time: '15 min' },
    { text: '通读一遍，标记修改处', time: '15 min' }
  ]
};

var DEFAULT_STEPS = [
  { text: '明确这件事的最终目标是什么', time: '5 min' },
  { text: '写下第一个最小动作', time: '5 min' },
  { text: '列出所有需要的资源/材料', time: '10 min' },
  { text: '把大步骤拆成15分钟内的小步骤', time: '15 min' },
  { text: '给每个小步骤排优先级', time: '5 min' },
  { text: '从最简单的步骤开始做', time: '15 min' },
  { text: '完成后奖励自己', time: '5 min' }
];

Page({
  data: {
    taskText: '',
    steps: [],
    doneCount: 0,
    progressPct: 0
  },

  onTaskInput: function(e) {
    this.setData({ taskText: e.detail.value });
  },

  breakdown: function() {
    var text = this.data.taskText.trim();
    if (!text) return;

    var steps = DEFAULT_STEPS;
    for (var key in TASK_TEMPLATES) {
      if (text.includes(key)) {
        steps = TASK_TEMPLATES[key].map(function(s) { return { text: s.text, time: s.time, done: false }; });
        break;
      }
    }
    if (steps === DEFAULT_STEPS) {
      steps = DEFAULT_STEPS.map(function(s) { return { text: s.text, time: s.time, done: false }; });
    }

    this.setData({ steps: steps, doneCount: 0, progressPct: 0 });
  },

  toggleStep: function(e) {
    var idx = e.currentTarget.dataset.index;
    var key = 'steps[' + idx + '].done';
    var newVal = !this.data.steps[idx].done;
    var obj = {};
    obj[key] = newVal;

    var doneCount = this.data.doneCount + (newVal ? 1 : -1);
    var total = this.data.steps.length;
    obj.doneCount = doneCount;
    obj.progressPct = Math.round((doneCount / total) * 100);

    this.setData(obj);
  }
});
