import os
import re
import subprocess
import json
from openai import OpenAI

max_calls=10
now_calls=0
exit_status=None

client=OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)


def query_lm(messages):
    response=client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        stream=False,
    )
    return response.choices[0].message.content

def parse_action(lm_output):
   matches=re.findall(
    r"```bash-action\s*\n(.*?)\n```",
    lm_output,
    re.DOTALL
   )
   if matches:
    return matches[0].strip()

   return "" 

def execute_action(command):
    result=subprocess.run(
        command,
        shell=True,
        text=True,
        env=os.environ,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
    )
    return {"output":result.stdout,
     "returncode": result.returncode }

messages = [
    {
        "role": "system",
        "content": """
You are a software engineering agent.

When you want to execute a terminal command, output exactly one command using:

```bash-action
<command>
```

Use terminal commands to inspect files, modify files, and run tests.

When the task is completely finished, output:

```bash-action
exit
```
"""
    },
    {
        "role": "user",
        "content": "Fix the buggy_project. Find the bug and make all tests pass."
    }
 ]
   
while True :
    if now_calls>=max_calls:
        messages.append({
        "role":"user",
        "content":"your used times is up to max"
        })
        exit_status="call_limit"
        break
    lm_output=query_lm(messages)
    print(lm_output)
    now_calls+=1
    messages.append({
        "role":"assistant",
        "content":lm_output
    })
    action=parse_action(lm_output)
    if not action:
        messages.append({
            "role":"user",
            "content":"you did not provide a valid bash-action.Please provide exactly one"
        })
        continue
        #跳过接下来的部分
    if action=="exit":
        exit_status="project_done"
        break
    print (action)
    result=execute_action(action)
    observation=f"""
    command output:
    {result["output"]}
     
    return code:
    {result["returncode"]} 
    
    """
    print(observation)
    messages.append({
        "role":"user",
        "content":observation
        
    })
trajectory={
    "message":messages,
    "exit_status":exit_status,
    "now_calls":now_calls,
}

with open("trajectory.json", "w", encoding="utf-8") as f:
    json.dump(
        trajectory,
        f,
        ensure_ascii=False,
        indent=2
        # 每一层缩进两格
    )    