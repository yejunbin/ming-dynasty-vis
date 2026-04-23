#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并所有7卷的LLM提取数据，生成 ming_all.json
"""

import json
import re
import os
import glob

def parse_appearance_time(at):
    if at is None:
        return None
    if isinstance(at, (int, float)):
        return int(at)
    s = str(at).strip()
    if s.isdigit():
        return int(s)
    m = re.search(r'\((\d{4})', s)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d{4})', s)
    if m:
        year = int(m.group(1))
        if 1200 <= year <= 1700:
            return year
    desc_map = {
        '元末': 1340, '元朝末年': 1340, '元朝末期': 1340,
        '至正年间': 1350, '至正初年': 1341, '至正中期': 1355, '至正末年': 1367,
        '洪武年间': 1375, '洪武初年': 1370, '洪武中期': 1380, '洪武末年': 1395,
        '建文年间': 1399, '建文': 1399,
        '永乐年间': 1410, '永乐初年': 1403, '永乐中期': 1415, '永乐末年': 1422,
        '洪熙': 1425, '宣德年间': 1430, '宣德': 1430,
        '正统年间': 1440, '正统': 1440, '景泰': 1450,
        '天顺': 1457, '成化': 1465, '弘治': 1490,
        '正德年间': 1510, '正德': 1510,
        '嘉靖年间': 1540, '嘉靖初年': 1522, '嘉靖中期': 1545, '嘉靖末年': 1566,
        '隆庆': 1567, '万历年间': 1590, '万历初年': 1573, '万历中期': 1590, '万历末年': 1619,
        '泰昌': 1620, '天启年间': 1625, '天启': 1625,
        '崇祯年间': 1635, '崇祯初年': 1628, '崇祯中期': 1635, '崇祯末年': 1643,
        '元初': 1280, '明初': 1368, '明初时期': 1370,
        '明中期': 1500, '明中后期': 1550, '明末': 1620,
        '少年时期': 1340, '青年时期': 1350, '中年时期': 1370, '晚年': 1390,
        '不详': None, '未知': None,
    }
    for key, val in desc_map.items():
        if key in s:
            return val
    return None

# ========== 收集所有卷数据 ==========
all_persons_raw = {}
all_relations_raw = []
all_events_raw = []

for vol_num in range(1, 8):
    pr_path = f'/Disk1/development/App/ming/data/vol{vol_num}_persons_relations.json'
    ev_path = f'/Disk1/development/App/ming/data/vol{vol_num}_events.json'

    if not os.path.exists(pr_path):
        print(f"⚠️ 跳过卷{vol_num}：人物关系文件不存在")
        continue
    if not os.path.exists(ev_path):
        print(f"⚠️ 跳过卷{vol_num}：事件文件不存在")
        continue

    with open(pr_path, 'r', encoding='utf-8') as f:
        pr_data = json.load(f)

    with open(ev_path, 'r', encoding='utf-8') as f:
        ev_data = json.load(f)

    # Merge persons
    for p in pr_data.get('persons', []):
        name = p.get('name', '')
        if not name:
            continue
        p['volume'] = vol_num
        if name not in all_persons_raw:
            all_persons_raw[name] = p
        else:
            existing = all_persons_raw[name]
            for alias in p.get('aliases', []):
                if alias not in existing.get('aliases', []):
                    existing.setdefault('aliases', []).append(alias)
            if p.get('birthYear') and not existing.get('birthYear'):
                existing['birthYear'] = p['birthYear']
            if p.get('deathYear') and not existing.get('deathYear'):
                existing['deathYear'] = p['deathYear']
            if len(p.get('bio', '')) > len(existing.get('bio', '')):
                existing['bio'] = p['bio']
            existing.setdefault('chapters', []).extend(p.get('chapters', []))
            # Keep earliest volume
            if vol_num < existing.get('volume', 99):
                existing['volume'] = vol_num

    for r in pr_data.get('relations', []):
        r['volume'] = vol_num
        all_relations_raw.append(r)

    for ev in ev_data:
        ev['volume'] = vol_num
        all_events_raw.append(ev)

    print(f"✅ 卷{vol_num}: {len(pr_data.get('persons', []))} 人, {len(pr_data.get('relations', []))} 关系, {len(ev_data)} 事件")

print(f"\n总计原始: {len(all_persons_raw)} 人, {len(all_relations_raw)} 关系, {len(all_events_raw)} 事件")

# ========== 过滤核心人物 ==========
# 保留出现2+章节的人物，或关系度较高的人物
chapter_counts = {}
for p in all_persons_raw.values():
    name = p.get('name', '')
    if name:
        chapter_counts[name] = len(set(p.get('chapters', [])))

# 计算关系度
degree_map = {}
for r in all_relations_raw:
    s, t = r.get('source', ''), r.get('target', '')
    if s: degree_map[s] = degree_map.get(s, 0) + 1
    if t: degree_map[t] = degree_map.get(t, 0) + 1

# 核心人物：出现2+章 或 关系度>=3 或 有明确生卒年
extra_names = {'朱元璋', '朱棣', '朱允炆', '朱高炽', '朱瞻基', '朱祁镇', '朱祁钰', '朱见深', '朱祐樘',
               '朱厚照', '朱厚熜', '朱载坖', '朱翊钧', '朱常洛', '朱由校', '朱由检',
               '马皇后', '徐达', '刘基', '姚广孝', '郑和', '于谦', '王守仁', '严嵩', '张居正',
               '戚继光', '海瑞', '袁崇焕', '魏忠贤', '李自成', '皇太极', '多尔衮', '吴三桂'}

core_persons = []
for p in all_persons_raw.values():
    name = p.get('name', '')
    ch_count = chapter_counts.get(name, 0)
    deg = degree_map.get(name, 0)
    has_bio = bool(p.get('bio'))
    has_years = bool(p.get('birthYear') or p.get('deathYear'))

    if name in extra_names or ch_count >= 2 or deg >= 3 or (has_years and has_bio):
        core_persons.append(p)

# 去重并附加最早出场时间
person_appearances = {}
for p in all_persons_raw.values():
    name = p.get('name', '')
    if not name:
        continue
    at = parse_appearance_time(p.get('appearanceTime'))
    if at is not None:
        if name not in person_appearances or at < person_appearances[name]:
            person_appearances[name] = at

seen = set()
unique_persons = []
for p in core_persons:
    if p['name'] not in seen:
        seen.add(p['name'])
        p['firstAppearanceYear'] = person_appearances.get(p['name'])
        unique_persons.append(p)

core_names = {p['name'] for p in unique_persons}
print(f"核心人物: {len(unique_persons)}")

# ========== 过滤关系 ==========
TYPE_MAP = {
    '君臣（名义上）': '君臣',
    '君臣(名义上)': '君臣',
}

relations_filtered = []
rel_set = set()
for r in all_relations_raw:
    src = r.get('source', '')
    tgt = r.get('target', '')
    if src not in core_names or tgt not in core_names:
        continue
    if src == tgt:
        continue
    t = r.get('type', '关联')
    t = TYPE_MAP.get(t, t)
    r['type'] = t
    key = (tuple(sorted([src, tgt])), t)
    if key in rel_set:
        continue
    rel_set.add(key)
    relations_filtered.append(r)

print(f"过滤后关系: {len(relations_filtered)}")

# ========== 处理事件 ==========
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
        p_clean = re.sub(r'[（(].*?[）)]', '', p_clean).strip()
        if p_clean in core_names and p_clean not in cleaned:
            cleaned.append(p_clean)
    return cleaned

events_clean = []
for ev in all_events_raw:
    clean_ps = clean_event_persons(ev.get('persons', []), core_names)
    if len(clean_ps) >= 1:
        ev['persons'] = clean_ps
        events_clean.append(ev)

# 按年份排序
def get_event_year(ev):
    y = ev.get('year')
    if y is None and ev.get('years'):
        y = ev['years'][0]
    try:
        return int(y)
    except (TypeError, ValueError):
        return 9999

events_clean.sort(key=lambda x: (get_event_year(x), -x.get('importance', 3)))
# 重新分配全局ID
for i, ev in enumerate(events_clean):
    ev['id'] = f'ev{i}'

print(f"清理后事件: {len(events_clean)}")

# 先建立人物->事件年份映射
person_event_years = {}
for ev in events_clean:
    y = get_event_year(ev)
    if y == 9999:
        continue
    for pname in ev.get('persons', []):
        if pname not in person_event_years:
            person_event_years[pname] = []
        person_event_years[pname].append(y)

# ========== 构建输出 ==========
person_objs = []
for p in unique_persons:
    name = p['name']
    p_events = [ev['id'] for ev in events_clean if name in ev['persons']]
    event_years = sorted(person_event_years.get(name, []))

    by = p.get('birthYear')
    dy = p.get('deathYear')
    fa = p.get('firstAppearanceYear')

    # startYear: 优先 firstAppearanceYear, 其次 birthYear, 再其次关联事件最早年份
    if fa is not None:
        start = fa
    elif by is not None:
        start = by
    elif event_years:
        start = event_years[0]
    else:
        start = None

    # endYear: 优先 deathYear, 其次关联事件最晚年份 + 5
    if dy is not None:
        end = dy
    elif event_years:
        end = event_years[-1] + 5
    else:
        end = None

    # 如果既没有 start 也没有 end，尝试从 volume 推断大致年代
    if start is None:
        vol = p.get('volume', 1)
        vol_starts = {1: 1328, 2: 1398, 3: 1424, 4: 1435, 5: 1521, 6: 1572, 7: 1620}
        start = vol_starts.get(vol, 1500)
    if end is None:
        end = start + 30

    person_objs.append({
        'id': name,
        'name': name,
        'startYear': start,
        'endYear': end,
        'intro': p.get('bio', ''),
        'events': p_events,
        'firstAppearance': 0,
        'identity': p.get('identity', ''),
        'aliases': p.get('aliases', []),
        'volume': p.get('volume', 1),
    })

relation_objs = []
for r in relations_filtered:
    relation_objs.append({
        'source': r['source'],
        'target': r['target'],
        'types': [r['type']],
        'context': r.get('description', ''),
        'volume': r.get('volume', 1),
    })

event_objs = []
for ev in events_clean:
    year = ev.get('year')
    if year is None and ev.get('years'):
        year = ev['years'][0]
    event_objs.append({
        'id': ev['id'],
        'title': ev['title'],
        'years': [year] if year else [],
        'persons': ev['persons'],
        'summary': ev.get('summary', ''),
        'importance': ev.get('importance', 3),
        'chapter': ev.get('chapter', ''),
        'volume': ev.get('volume', 1),
    })

# 时间轴数据
timeline = [
    {'year': 1328, 'label': '朱元璋出生', 'emperor': '元顺帝', 'era': '至正'},
    {'year': 1368, 'label': '明朝建立', 'emperor': '朱元璋', 'era': '洪武'},
    {'year': 1398, 'label': '洪武驾崩', 'emperor': '朱元璋', 'era': '洪武'},
    {'year': 1402, 'label': '靖难成功', 'emperor': '朱棣', 'era': '永乐'},
    {'year': 1424, 'label': '永乐驾崩', 'emperor': '朱棣', 'era': '永乐'},
    {'year': 1449, 'label': '土木堡之变', 'emperor': '朱祁镇', 'era': '正统'},
    {'year': 1550, 'label': '庚戌之变', 'emperor': '朱厚熜', 'era': '嘉靖'},
    {'year': 1572, 'label': '隆庆开关', 'emperor': '朱载坖', 'era': '隆庆'},
    {'year': 1582, 'label': '张居正去世', 'emperor': '朱翊钧', 'era': '万历'},
    {'year': 1616, 'label': '后金建立', 'emperor': '朱翊钧', 'era': '万历'},
    {'year': 1627, 'label': '天启驾崩', 'emperor': '朱由校', 'era': '天启'},
    {'year': 1644, 'label': '明朝灭亡', 'emperor': '朱由检', 'era': '崇祯'},
]

output = {
    'volume': '明朝那些事儿（全七卷）',
    'timeRange': [1328, 1644],
    'timeline': timeline,
    'persons': person_objs,
    'events': event_objs,
    'relations': relation_objs,
}

with open('/Disk1/development/App/ming/data/ming_all.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

with open('/Disk1/development/App/ming/web/data/ming_all.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ 全部数据已保存")
print(f"   人物: {len(person_objs)}")
print(f"   事件: {len(event_objs)}")
print(f"   关系: {len(relation_objs)}")
print(f"   时间范围: 1328 - 1644")
