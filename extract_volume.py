#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用脚本：提取指定卷的人物、关系和事件。
用法：python3 extract_volume.py <卷号> <起始行> <结束行> [卷名]
"""

import os
import re
import json
import time
import sys
from openai import OpenAI

API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not API_KEY:
    env_path = '/Disk1/development/App/ming/.env'
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith('DEEPSEEK_API_KEY='):
                    API_KEY = line.split('=', 1)[1].strip()
                    break
if not API_KEY:
    print("错误：未设置 DEEPSEEK_API_KEY 环境变量")
    exit(1)

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

vol_num = int(sys.argv[1])
start_line = int(sys.argv[2])
end_line = int(sys.argv[3])
vol_name = sys.argv[4] if len(sys.argv) > 4 else f"第{vol_num}卷"

with open('/Disk1/development/App/ming/明朝那些事儿.txt', 'rb') as f:
    text = f.read().decode('gbk', errors='ignore')
lines = text.split('\n')
vol_lines = lines[start_line:end_line]

# 识别章节
chapters = []
chapter_pattern = re.compile(r'^第[一二三四五六七八九十]+章\s+')
for i, line in enumerate(vol_lines):
    s = line.strip()
    if chapter_pattern.match(s):
        chapters.append((i, s))

# 对于无章节标记的卷，按固定长度分块
if not chapters:
    chunk_size = 600
    for i in range(0, len(vol_lines), chunk_size):
        chunk_end = min(i + chunk_size, len(vol_lines))
        title = f"片段 {i//chunk_size + 1}"
        chapters.append((i, title))

print(f"[{vol_name}] 共 {len(chapters)} 个章节/片段，{len(vol_lines)} 行")

# ========== 提取人物和关系 ==========
PERSON_PROMPT = """你是中国历史专家。请根据以下《明朝那些事儿》章节内容，提取所有出现的历史人物及其关系。

要求：
1. **人物**字段：
   - name: 人物全名（优先用常用名）
   - aliases: 别名列表
   - identity: 身份
   - birthYear: 生年（整数，不详则null）
   - deathYear: 卒年（整数，不详则null）
   - bio: 一句话简介（50字以内）
   - appearanceTime: 本章中该人物出场的时间（尽量精确到年份，模糊写如"永乐初年(1403-1405)")

2. **关系**字段：
   - source: 人物A
   - target: 人物B
   - type: 关系类型（只选一种：君臣/敌对/亲属/朋友/同盟/师生/关联）
   - description: 关系简述

3. 只提取本章实际提到的人物和关系，不要编造。

输出格式：
{"persons": [...], "relations": [...]}

章节内容：
{content}
"""

all_persons = {}
all_relations = []

for idx, (start, title) in enumerate(chapters):
    end_pos = chapters[idx + 1][0] if idx + 1 < len(chapters) else len(vol_lines)
    chapter_text = '\n'.join(vol_lines[start:end_pos])

    if len(chapter_text) > 8000:
        chapter_text = chapter_text[:8000] + "\n...（内容截断）"

    print(f"\n[{vol_name} {idx+1}/{len(chapters)}] 人物: {title} ({len(chapter_text)} 字符)")

    prompt = PERSON_PROMPT.replace("{content}", chapter_text)
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个严谨的中国历史研究者，擅长从文本中提取结构化历史数据。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4000,
        )
        content = response.choices[0].message.content.strip()
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        result = json.loads(content)
        for p in result.get('persons', []):
            name = p.get('name', '')
            if not name:
                continue
            if name not in all_persons:
                all_persons[name] = p
                all_persons[name]['chapters'] = [title]
            else:
                existing = all_persons[name]
                for alias in p.get('aliases', []):
                    if alias not in existing.get('aliases', []):
                        existing.setdefault('aliases', []).append(alias)
                if p.get('birthYear') and not existing.get('birthYear'):
                    existing['birthYear'] = p['birthYear']
                if p.get('deathYear') and not existing.get('deathYear'):
                    existing['deathYear'] = p['deathYear']
                if len(p.get('bio', '')) > len(existing.get('bio', '')):
                    existing['bio'] = p['bio']
                existing['chapters'].append(title)

        for r in result.get('relations', []):
            r['chapter'] = title
            r['volume'] = vol_num
            all_relations.append(r)

        print(f"  提取到 {len(result.get('persons', []))} 个人物, {len(result.get('relations', []))} 条关系")
    except Exception as e:
        print(f"  错误: {e}")
        with open(f'/Disk1/development/App/ming/data/vol{vol_num}_persons_partial.json', 'w', encoding='utf-8') as f:
            json.dump({'persons': list(all_persons.values()), 'relations': all_relations}, f, ensure_ascii=False, indent=2)
        continue

    time.sleep(1)

out = {'persons': list(all_persons.values()), 'relations': all_relations}
out_path = f'/Disk1/development/App/ming/data/vol{vol_num}_persons_relations.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"\n  人物关系保存至: {out_path} ({len(all_persons)} 人, {len(all_relations)} 关系)")

# ========== 提取事件 ==========
EVENT_PROMPT = """你是中国历史专家。请根据以下《明朝那些事儿》章节内容，提取5-10个关键历史事件。

要求：
1. 每个事件包含：题目（简短标题）、时间（公元年份）、涉及人物（列表）、事件简介（50-100字）、重要性（1-5分）
2. 事件必须是该章节中实际发生或提及的，不要编造
3. 时间尽量精确，年号请转换为公元年份
4. 只输出JSON数组

输出格式示例：
[{"title": "...", "year": 1368, "persons": ["..."], "summary": "...", "importance": 5}]

章节内容：
{content}
"""

all_events = []

for idx, (start, title) in enumerate(chapters):
    end_pos = chapters[idx + 1][0] if idx + 1 < len(chapters) else len(vol_lines)
    chapter_text = '\n'.join(vol_lines[start:end_pos])

    if len(chapter_text) > 6000:
        chapter_text = chapter_text[:6000] + "\n...（内容截断）"

    print(f"\n[{vol_name} {idx+1}/{len(chapters)}] 事件: {title} ({len(chapter_text)} 字符)")

    prompt = EVENT_PROMPT.replace("{content}", chapter_text)
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个严谨的中国历史研究者，擅长从文本中提取结构化历史事件。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        content = response.choices[0].message.content.strip()
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()

        events = json.loads(content)
        for ev in events:
            ev['chapter'] = title
            ev['volume'] = vol_num
            ev['id'] = f"ev_v{vol_num}_{len(all_events)}"
            all_events.append(ev)

        print(f"  提取到 {len(events)} 个事件")
    except Exception as e:
        print(f"  错误: {e}")
        with open(f'/Disk1/development/App/ming/data/vol{vol_num}_events_partial.json', 'w', encoding='utf-8') as f:
            json.dump(all_events, f, ensure_ascii=False, indent=2)
        continue

    time.sleep(1)

events_path = f'/Disk1/development/App/ming/data/vol{vol_num}_events.json'
with open(events_path, 'w', encoding='utf-8') as f:
    json.dump(all_events, f, ensure_ascii=False, indent=2)
print(f"\n  事件保存至: {events_path} ({len(all_events)} 个事件)")
print(f"\n✅ [{vol_name}] 完成！")
