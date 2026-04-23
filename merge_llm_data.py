#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并 LLM 提取的人物、关系、事件数据，生成前端可用的 ming_vol1.json
"""

import json
import re

# 加载数据
with open('/Disk1/development/App/ming/data/persons_relations_llm.json', 'r', encoding='utf-8') as f:
    llm = json.load(f)

with open('/Disk1/development/App/ming/data/events_llm.json', 'r', encoding='utf-8') as f:
    events_llm = json.load(f)

# ========== 过滤人物 ==========
# 保留出现2+章节的人物
persons_raw = llm['persons']
core_persons = [p for p in persons_raw if len(p.get('chapters', [])) >= 2]

# 额外保留一些虽然只出现1章但重要的历史人物
extra_names = {'朱五四', '陈氏', '马姑娘', '马皇后', '韩山童', '彭莹玉', '邹普胜', '张明鉴', '八思尔不花', '缪大亨', '俞通海', '张天祐', '张士义', '张士德', '郭子兴之子', '郭子兴儿子', '冯国用', '冯国胜', '花云', '李贞', '朱重四', '朱重六', '丁普郎', '胡大海', '孙炎', '廖永忠', '郭桓', '郑士利', '袁凯', '罗复仁', '朱亮祖', '纳哈出', '观童', '李成桂', '爱猷识', '天保奴', '李景隆', '杨宪', '汪广洋', '扩廓帖木儿', '薛显', '耿炳文'}

for p in persons_raw:
    if p['name'] in extra_names and p not in core_persons:
        core_persons.append(p)

# 解析 appearanceTime 为数字年份
def parse_appearance_time(at):
    """将 appearanceTime 转换为整数年份"""
    if at is None:
        return None
    if isinstance(at, (int, float)):
        return int(at)
    s = str(at).strip()
    # 直接是整数
    if s.isdigit():
        return int(s)
    # 提取括号内的年份，如 "洪武初年(1368-1372)"
    m = re.search(r'\((\d{4})', s)
    if m:
        return int(m.group(1))
    # 提取开头的4位数字
    m = re.search(r'(\d{4})', s)
    if m:
        year = int(m.group(1))
        if 1300 <= year <= 1400:
            return year
    # 映射常见描述
    desc_map = {
        '元末': 1340, '元朝末年': 1340, '元朝末期': 1340,
        '至正年间': 1350, '至正初年': 1341, '至正中期': 1355, '至正末年': 1367,
        '洪武年间': 1375, '洪武初年': 1370, '洪武中期': 1380, '洪武末年': 1395,
        '元初': 1280, '明初': 1368, '明初时期': 1370,
        '少年时期': 1340, '青年时期': 1350, '中年时期': 1370, '晚年': 1390,
        '不详': None, '未知': None,
    }
    for key, val in desc_map.items():
        if key in s:
            return val
    return None

# 为每个人物收集所有 appearanceTime，取最早的
person_appearances = {}
for p in persons_raw:
    name = p.get('name', '')
    if not name:
        continue
    at = parse_appearance_time(p.get('appearanceTime'))
    if at is not None:
        if name not in person_appearances or at < person_appearances[name]:
            person_appearances[name] = at

# 去重并排序
seen = set()
unique_persons = []
for p in core_persons:
    if p['name'] not in seen:
        seen.add(p['name'])
        # 附加最早的出场时间
        p['firstAppearanceYear'] = person_appearances.get(p['name'])
        unique_persons.append(p)

core_names = {p['name'] for p in unique_persons}
print(f"核心人物: {len(unique_persons)}")
for p in unique_persons:
    by = p.get('birthYear') or '?' ; dy = p.get('deathYear') or '?'
    fa = p.get('firstAppearanceYear') or '?'
    print(f"  {p['name']:12s} 出场:{fa}  生卒:{by}-{dy}  {p.get('identity', '')}")

# ========== 过滤关系 ==========
relations_raw = llm['relations']

# 关系类型映射
TYPE_MAP = {
    '君臣（名义上）': '君臣',
    '君臣(名义上)': '君臣',
}

relations_filtered = []
rel_set = set()
for r in relations_raw:
    src = r.get('source', '')
    tgt = r.get('target', '')
    if src not in core_names or tgt not in core_names:
        continue
    if src == tgt:
        continue

    t = r.get('type', '关联')
    t = TYPE_MAP.get(t, t)
    r['type'] = t

    # 去重（按有序对+类型）
    key = (tuple(sorted([src, tgt])), t)
    if key in rel_set:
        continue
    rel_set.add(key)

    relations_filtered.append(r)

print(f"\n过滤后关系: {len(relations_filtered)}")
from collections import Counter
type_counts = Counter(r['type'] for r in relations_filtered)
for t, c in type_counts.most_common():
    print(f"  {t}: {c}")

# ========== 处理事件 ==========
# 使用之前 LLM 提取的 159 个事件，清理人物名
def clean_event_persons(persons_list, core_names):
    cleaned = []
    alias_map = {
        '朱重八': '朱元璋', '朱重八（朱元璋）': '朱元璋',
        '马姑娘': '马皇后', '马氏': '马皇后',
        '王保保': '扩廓帖木儿',
        '胡惟': '胡惟庸',
        '陈氏（母）': '陈氏', '朱五四（父）': '朱五四',
        '朱重四（兄）': '朱重四', '朱重八侄': '朱重八',
    }
    for p in persons_list:
        p_clean = alias_map.get(p, p)
        # 去除括号注释
        p_clean = re.sub(r'[（(].*?[）)]', '', p_clean).strip()
        if p_clean in core_names and p_clean not in cleaned:
            cleaned.append(p_clean)
    return cleaned

events_clean = []
for ev in events_llm:
    clean_ps = clean_event_persons(ev.get('persons', []), core_names)
    if len(clean_ps) >= 1:  # 至少保留1人
        ev['persons'] = clean_ps
        events_clean.append(ev)

# 按年份排序
events_clean.sort(key=lambda x: (x.get('year') or 9999, -x.get('importance', 3)))
# 重新分配ID
for i, ev in enumerate(events_clean):
    ev['id'] = f'ev{i}'

print(f"\n清理后事件: {len(events_clean)}")

# ========== 构建输出 ==========
# 人物对象
person_objs = []
for p in unique_persons:
    by = p.get('birthYear') or 1328
    dy = p.get('deathYear') or 1398
    # 关联事件
    p_events = [ev['id'] for ev in events_clean if p['name'] in ev['persons']]

    # 使用 firstAppearanceYear 作为 startYear（圆的位置）
    start = p.get('firstAppearanceYear') or by
    # 如果没有 deathYear，尝试从事件推断最晚出场时间
    end = dy

    person_objs.append({
        'id': p['name'],
        'name': p['name'],
        'startYear': start,
        'endYear': end,
        'intro': p.get('bio', ''),
        'events': p_events,
        'firstAppearance': 0,
        'identity': p.get('identity', ''),
        'aliases': p.get('aliases', []),
    })

# 关系对象（转换为前端格式）
relation_objs = []
for r in relations_filtered:
    relation_objs.append({
        'source': r['source'],
        'target': r['target'],
        'types': [r['type']],
        'context': r.get('description', ''),
    })

# 事件对象
event_objs = []
for ev in events_clean:
    event_objs.append({
        'id': ev['id'],
        'title': ev['title'],
        'years': [ev['year']] if ev.get('year') else [],
        'persons': ev['persons'],
        'summary': ev.get('summary', ''),
        'importance': ev.get('importance', 3),
        'chapter': ev.get('chapter', ''),
    })

output = {
    'volume': '第壹卷 朱元璋篇',
    'timeRange': [1328, 1398],
    'timeline': [
        {'year': 1328, 'label': '元末', 'emperor': '元顺帝', 'era': '至正'},
        {'year': 1368, 'label': '明朝建立', 'emperor': '朱元璋', 'era': '洪武'},
        {'year': 1398, 'label': '洪武驾崩', 'emperor': '朱元璋', 'era': '洪武'},
    ],
    'persons': person_objs,
    'events': event_objs,
    'relations': relation_objs,
}

with open('/Disk1/development/App/ming/data/ming_vol1.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

with open('/Disk1/development/App/ming/web/data/ming_vol1.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ 数据已保存")
print(f"   人物: {len(person_objs)}")
print(f"   事件: {len(event_objs)}")
print(f"   关系: {len(relation_objs)}")
