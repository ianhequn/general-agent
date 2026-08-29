这是一个我的小项目 我将在大二的这一个学年学习从swe agent到sub agent 到 memory loop 到tool calling sub agent 做好sandbox plan mode
最终实现出自己的codex或者pi 
持续更新

v0：
实现最简单的ai loop 使用message同时接受observation和lm_output
注入os环境参数 sk deepseek api
使用最简单的add算法检验 agent是否能自主循环

v0.5
加上了returncode作为执行output 同时结构化observation 
添加了exit状态可以区分是完成任务 额度超限 
添加json 每一次运行结束保存 trajectory 里面有message returncode exit_status 以及now_calls引用次数
