#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 LLM 提取的事件整合到主数据中，清理人物名、修正年份
"""

import json
import re

# 加载数据
with open('/Disk1/development/App/ming/data/ming_vol1.json', 'r', encoding='utf-8') as f:
    main_data = json.load(f)

with open('/Disk1/development/App/ming/data/events_llm.json', 'r', encoding='utf-8') as f:
    llm_events = json.load(f)

# 核心人物名单（用于过滤）
core_persons = {p['name'] for p in main_data['persons']}

# 别名映射
alias_map = {
    '朱重八（朱元璋）': '朱元璋',
    '朱五四（父）': '朱五四',
    '陈氏（母）': '陈氏',
    '朱重四（兄）': '朱重四',
    '朱重八侄': '朱重八',
    '朱元璋（原名朱重八）': '朱元璋',
    '朱五四': '朱元璋',  # 朱元璋父亲，但核心人物列表中没有，映射到朱元璋
    '陈氏': '朱元璋',   # 同上
    '朱重四': '朱元璋',
    '马皇后': '马氏',
    '胡惟': '胡惟庸',
    '王保保': '扩廓帖木儿',
    '文天祥': None,  # 不在核心人物中
    '脱脱': None,
    '刘德': None,
    '朱允炆': '朱标',  # 近似
}

def clean_person(name):
    # 去除括号注释
    name = re.sub(r'[（(].*?[）)]', '', name).strip()
    if name in alias_map:
        return alias_map[name]
    if name in core_persons:
        return name
    # 尝试模糊匹配
    for cp in core_persons:
        if cp in name or name in cp:
            return cp
    return None

def fix_year(year, title, chapter):
    if year is None:
        # 根据章节推断
        if '蓝玉' in chapter:
            return 1392
        if '胡惟庸' in chapter:
            return 1380
        if '建国' in chapter:
            return 1368
        return 1368
    if year < 1320:
        # 背景事件，保留原年份但标记
        return year
    if year > 1398:
        return 1398
    return year

new_events = []
for ev in llm_events:
    # 清理人物
    clean_persons = []
    for p in ev.get('persons', []):
        cp = clean_person(p)
        if cp and cp not in clean_persons:
            clean_persons.append(cp)

    # 如果清理后只剩1人，尝试保留
    year = fix_year(ev.get('year'), ev['title'], ev['chapter'])

    new_ev = {
        'id': ev['id'],
        'title': ev['title'],
        'years': [year],
        'persons': clean_persons,
        'summary': ev.get('summary', ''),
        'importance': ev.get('importance', 3),
        'chapter': ev['chapter'],
    }
    new_events.append(new_ev)

# 按年份排序
new_events.sort(key=lambda x: (x['years'][0] if x['years'] else 9999, -x['importance']))

# 更新主数据
main_data['events'] = new_events

# 更新人物的事件关联
person_event_map = {p['name']: [] for p in main_data['persons']}
for ev in new_events:
    for p in ev['persons']:
        if p in person_event_map:
            person_event_map[p].append(ev['id'])

for p in main_data['persons']:
    p['events'] = person_event_map.get(p['name'], [])

with open('/Disk1/development/App/ming/data/ming_vol1.json', 'w', encoding='utf-8') as f:
    json.dump(main_data, f, ensure_ascii=False, indent=2)

# 同时复制到 web/data/
with open('/Disk1/development/App/ming/web/data/ming_vol1.json', 'w', encoding='utf-8') as f:
    json.dump(main_data, f, ensure_ascii=False, indent=2)

print(f"✅ 整合完成！")
print(f"   总事件数: {len(new_events)}")
print(f"   重要性分布:")
from collections import Counter
dist = Counter(e['importance'] for e in new_events)
for k in sorted(dist.keys()):
    print(f"     {k}分: {dist[k]}个")
print(f"\n   人物事件关联更新完成")
for p in main_data['persons'][:10]:
    print(f"     {p['name']}: {len(p['events'])}个事件")
