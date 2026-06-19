#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate interactive quiz HTML for 西部计划 topics."""
import json, os, re

DIR = os.path.dirname(os.path.abspath(__file__))

def read(fname):
    with open(os.path.join(DIR, fname), 'r', encoding='utf-8') as f:
        return f.read()

def parse_std(text):
    """Parse format: numbered questions with options and 答案：X"""
    questions = []
    lines = text.split('\n')
    in_ref = False
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        if '参考答案' in line:
            in_ref = True
            continue
        if in_ref:
            continue
        if '张远山' in line or '说明' in line or line.startswith('一、') or line.startswith('二、'):
            continue
        if line.startswith('（') and '）' in line[:15]:
            continue

        # Question with number
        m = re.match(r'(\d+)\.\s*(.*)', line)
        if not m:
            continue

        qtext = m.group(2).strip()
        ans = None
        opts = []

        # Look for inline answer
        am = re.search(r'答案[：:]([A-Z]+)', qtext)
        if am:
            ans = am.group(1)
            qtext = re.sub(r'答案[：:][A-Z]+', '', qtext).strip()

        # Collect options
        while i < len(lines):
            l = lines[i].strip()
            if not l:
                i += 1
                continue
            om = re.match(r'([A-E])[、．.]\s*(.*)', l)
            if om:
                opts.append(om.group(2).strip())
                i += 1
                continue
            if '答案' in l:
                am2 = re.search(r'答案[：:]([A-Z\d]+)', l)
                if am2 and not ans:
                    ans = am2.group(1)
                i += 1
                break
            if re.match(r'\d+\.', l) or '解析' in l:
                break
            i += 1

        if qtext and ans:
            ai = ord(ans[0]) - ord('A') if ans[0].isalpha() else 0
            if opts and ai >= len(opts):
                ai = len(opts) - 1
            questions.append({'q': qtext, 'opts': opts, 'ans': ai, 'type': 'choice'})
    return questions


def parse_20da(text):
    """Parse 20大报告 fill-in: number + text + 答案：xxx"""
    qs = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'(\d+)\s+(.*?)(?:答案[：:])(.*)', line)
        if m:
            qs.append({'q': m.group(2).strip(), 'ans': m.group(3).strip(), 'type': 'fill'})
    return qs


def parse_sanzhong(text):
    """Parse 三中全会: mixed types in one file"""
    qs = []
    for line in text.split('\n'):
        line = line.strip()
        if not line or '张远山' in line:
            continue
        m = re.match(r'(\d+)\.\s*(.*?)(?:答案[：:]?\s*)([A-Z\d对错]+)', line)
        if not m:
            continue
        qtext = m.group(2).strip()
        ans_text = m.group(3).strip()

        # Check for judge
        if ans_text in ['对', '错', '√', '×']:
            qs.append({'q': qtext, 'ans': 0 if ans_text in ['对', '√'] else 1, 'opts': ['正确', '错误'], 'type': 'choice'})
            continue

        # Check for inline options
        opt_matches = list(re.finditer(r'([A-E])[.．、]\s*([^A-E]+?)(?=[A-E][.．、]|$)', qtext))
        if opt_matches:
            ctext = qtext[:opt_matches[0].start()].strip()
            copts = [m.group(2).strip().rstrip('，。；') for m in opt_matches]
            ai = ord(ans_text[0]) - ord('A') if ans_text[0].isalpha() else 0
            if ai >= len(copts):
                ai = len(copts) - 1
            qs.append({'q': ctext, 'opts': copts, 'ans': ai, 'type': 'choice'})
        elif len(ans_text) > 2:
            qs.append({'q': qtext, 'ans': ans_text, 'type': 'fill'})
        else:
            qs.append({'q': qtext, 'ans': 0, 'opts': ['A', 'B', 'C', 'D'], 'type': 'choice'})
    return qs


def parse_tuan(text):
    """Parse 共青团: (√) (×) or (A) (B) etc. Multi-line options."""
    qs = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or '专业知识' in line or '专业知识' in line:
            continue

        # True/false: (√) or (×)
        m = re.match(r'(\d+)[.、]\s*(.*?)\(\s*([√×])\s*\)', line)
        if m:
            qs.append({'q': m.group(2).strip().rstrip('，。；'), 'ans': 0 if m.group(3) == '√' else 1,
                       'opts': ['正确', '错误'], 'type': 'choice'})
            continue

        # Choice: (A) (B) etc - check for number at start
        m2 = re.match(r'(\d+)[.、]\s*(.*?)\(\s*([A-E])\s*\)', line)
        if not m2:
            continue

        qtext = m2.group(2).strip()
        ans_letter = m2.group(3)

        # Collect options from following lines
        opts = []
        while i < len(lines):
            l = lines[i].strip()
            if not l:
                i += 1; continue
            om = re.match(r'([A-E])[、．.]\s*(.*)', l)
            if om:
                opt_text = om.group(2).strip()
                # Check if this line has multiple inline options (A、textB、textC、textD、text)
                sub_opts = re.split(r'(?=[A-E][、．.])', opt_text)
                if len(sub_opts) > 1:
                    for so in sub_opts:
                        so_clean = re.sub(r'^[A-E][、．.]\s*', '', so).strip()
                        if so_clean:
                            opts.append(so_clean)
                else:
                    opts.append(opt_text)
                i += 1
                continue
            if re.match(r'\d+[.、]', l):
                break
            i += 1

        if not opts:
            opts = ['A', 'B', 'C', 'D']

        ans_idx = ord(ans_letter) - ord('A')
        if ans_idx >= len(opts):
            ans_idx = 0
        qs.append({'q': qtext, 'ans': ans_idx, 'opts': opts, 'type': 'choice'})
    return qs


def parse_zhiyuan(text, answers=None):
    """Parse 志愿服务 with optional answer dict from PDF red text analysis."""
    qs = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        m = re.match(r'(\d+)[.、]?\s*(.*)', line)
        if not m:
            continue
        qnum = int(m.group(1))
        qtext = m.group(2).strip().rstrip('，。；（）')

        opts = []
        while i < len(lines):
            l = lines[i].strip()
            if not l:
                i += 1; continue
            om = re.match(r'([A-E])[、．.]\s*(.*)', l)
            if om:
                opt_text = om.group(2).strip()
                sub_opts = re.split(r'(?=[A-E][、．.])', opt_text)
                if len(sub_opts) > 1:
                    for so in sub_opts:
                        so_clean = re.sub(r'^[A-E][、．.]\s*', '', so).strip()
                        if so_clean:
                            opts.append(so_clean)
                else:
                    opts.append(opt_text)
                i += 1
                continue
            if re.match(r'\d+[.、]', l):
                break
            i += 1

        if not opts:
            continue
        if answers and qnum in answers:
            ans_idx = answers[qnum]
            if ans_idx >= len(opts):
                ans_idx = len(opts) - 1
            qs.append({'q': qtext, 'opts': opts, 'ans': ans_idx, 'type': 'choice'})
    return qs


def parse_dangshi(text):
    """Parse 党史国情: answer key at bottom like '1.【答案】D'"""
    # Extract answer key
    answers = {}
    for line in text.split('\n'):
        m = re.match(r'(\d+)\.\s*【答案】(\w+)', line)
        if m:
            answers[int(m.group(1))] = m.group(2)

    qs = []
    lines = text.split('\n')
    cur_q = ''
    cur_opts = []
    cur_num = 0

    for line in lines:
        line = line.strip()
        if not line or '专项练习' in line or '单项选择题' in line:
            continue
        if line.startswith('二、') or line.startswith('三、'):
            break

        m = re.match(r'(\d+)\.\s*(.*)', line)
        if m:
            if cur_num and cur_q and cur_opts:
                ans_text = answers.get(cur_num, 'A')
                ai = ord(ans_text[0]) - ord('A') if ans_text[0].isalpha() else 0
                if ai >= len(cur_opts): ai = len(cur_opts) - 1
                qs.append({'q': cur_q, 'opts': list(cur_opts), 'ans': ai, 'type': 'choice'})
            cur_num = int(m.group(1))
            cur_q = m.group(2).strip()
            cur_opts = []
            continue

        om = re.match(r'([A-E])[.．、]\s*(.*)', line)
        if om:
            cur_opts.append(om.group(2).strip())

    # Last question
    if cur_num and cur_q and cur_opts:
        ans_text = answers.get(cur_num, 'A')
        ai = ord(ans_text[0]) - ord('A') if ans_text[0].isalpha() else 0
        if ai >= len(cur_opts): ai = len(cur_opts) - 1
        qs.append({'q': cur_q, 'opts': cur_opts, 'ans': ai, 'type': 'choice'})

    return qs


# ===== BUILD ALL TOPICS =====
topics = []

# Standard format files
for fname, tname in [
    ('【2025中央经济工作会议】测试题+答案.txt', '2025中央经济工作会议'),
    ('【2026中央一号文件】测试题+答案.txt', '2026中央一号文件'),
    ('【2026全国两会】测试题+答案.txt', '2026全国两会'),
    ('【二十届四中全会】测试题+答案.txt', '二十届四中全会'),
]:
    qs = parse_std(read(fname))
    if qs:
        print(f'{tname}: {len(qs)} questions')
        topics.append({'name': tname, 'questions': qs})
    else:
        print(f'{tname}: EMPTY!')

# 20大报告
qs = parse_20da(read('【20大报告】练习题100题+答案.txt'))
if qs:
    print(f'20大报告: {len(qs)} questions')
    topics.append({'name': '20大报告', 'questions': qs})

# 三中全会
qs = parse_sanzhong(read('【二十届三中全会】测试题50题.txt'))
if qs:
    print(f'二十届三中全会: {len(qs)} questions')
    topics.append({'name': '二十届三中全会', 'questions': qs})

# 党史国情
qs = parse_dangshi(read('【党史国情】练习题+答案.txt'))
if qs:
    print(f'党史国情: {len(qs)} questions')
    # Split if too large
    if len(qs) > 90:
        mid = len(qs) // 2
        topics.append({'name': '党史国情(上)', 'questions': qs[:mid]})
        topics.append({'name': '党史国情(下)', 'questions': qs[mid:]})
    else:
        topics.append({'name': '党史国情', 'questions': qs})

# 共青团
qs = parse_tuan(read('【共青团知识】练习题+答案.txt'))
if qs:
    print(f'共青团知识: {len(qs)} questions')
    topics.append({'name': '共青团知识', 'questions': qs})

# 志愿服务（使用用户提供的标准答案）
zhiyuan_answers = {
    1:0,2:1,3:2,4:0,5:2,6:1,7:3,8:2,9:1,10:1,
    11:1,12:2,13:0,15:0,16:2,17:2,18:0,19:1,20:2,
    21:0,22:3,23:2,24:1,25:3,26:2,27:0,28:0,29:3,30:2,
    31:0,32:1,33:2,34:0,35:3,36:2,37:2,38:3,39:3,
    40:0,41:2,42:1,43:2,44:2,45:0,46:0,47:1,
    49:0,50:1,51:1,52:1,53:1,54:3,55:0,56:3,57:1,
    58:3,59:3,60:2,61:2,62:3,63:3,64:3,65:1,66:3,
    67:3,68:3,69:2,70:2,71:1,72:1,73:1,74:1,75:1,76:2,77:2
}

qs = parse_zhiyuan(read('【志愿服务工作】练习题+答案.txt'), zhiyuan_answers)
if qs:
    print(f'志愿服务工作: {len(qs)} questions')
    topics.append({'name': '志愿服务工作', 'questions': qs})

# ===== GENERATE HTML =====
total_qs = sum(len(t['questions']) for t in topics)
print(f'\nTotal: {len(topics)} topics, {total_qs} questions')

topics_json = json.dumps(topics, ensure_ascii=False)

# Read template
template_path = os.path.join(os.path.dirname(__file__), '..', 'python期末复习', 'python_quiz.html')
# Use embedded template instead
HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>西部计划·时政与常识测试题</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans SC",sans-serif;background:#f0f2f5;color:#333;padding:16px}
.container{max-width:920px;margin:0 auto}
h1{text-align:center;font-size:24px;margin-bottom:4px;color:#1a73e8}
.subtitle{text-align:center;color:#666;margin-bottom:14px;font-size:13px}
.tabs{display:flex;gap:5px;margin-bottom:14px;flex-wrap:wrap}
.tab-btn{padding:7px 12px;border:none;border-radius:5px;font-size:12px;font-weight:600;cursor:pointer;transition:.2s;background:#e8eaf0;color:#555;line-height:1.3;white-space:nowrap}
.tab-btn:hover{background:#d2d6e0}
.tab-btn.active{background:#1a73e8;color:#fff}
.tab-btn small{font-weight:400;font-size:10px}
.tab-content{display:none}
.tab-content.active{display:block}
.controls{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.controls button{padding:7px 16px;border:none;border-radius:5px;font-size:12px;font-weight:600;cursor:pointer}
.btn-reset{background:#ff6b6b;color:#fff}
.btn-show-all{background:#ffd43b;color:#333}
.btn-hide-all{background:#868e96;color:#fff}
.stats{background:#fff;border-radius:8px;padding:10px 14px;margin-bottom:14px;display:flex;flex-wrap:wrap;gap:6px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.stat-item{font-size:12px;color:#555;white-space:nowrap}
.stat-item span{font-weight:700;color:#1a73e8}
.question-card{background:#fff;border-radius:8px;padding:14px 18px;margin-bottom:10px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.q-header{font-size:13px;font-weight:600;margin-bottom:8px;line-height:1.5}
.q-number{display:inline-block;background:#1a73e8;color:#fff;border-radius:50%;width:22px;height:22px;text-align:center;line-height:22px;font-size:11px;margin-right:6px;flex-shrink:0}
.options{display:flex;flex-direction:column;gap:5px;margin:6px 0}
.option{display:flex;align-items:center;gap:6px;padding:7px 10px;border:2px solid #e0e0e0;border-radius:6px;cursor:pointer;font-size:12px;transition:.15s}
.option:hover{border-color:#90caf9;background:#f5f9ff}
.option.selected{border-color:#1a73e8;background:#e8f0fe}
.option.correct{border-color:#2e7d32;background:#e8f5e9}
.option.wrong{border-color:#c62828;background:#ffebee}
.option-letter{width:22px;height:22px;border-radius:50%;background:#f0f0f0;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:11px;flex-shrink:0}
.option.correct .option-letter,.option.selected .option-letter{color:#fff}
.option.correct .option-letter{background:#2e7d32}
.option.wrong .option-letter{background:#c62828;color:#fff}
.option.selected .option-letter{background:#1a73e8}
.fill-input{width:100%;padding:7px 10px;border:2px solid #e0e0e0;border-radius:6px;font-size:13px;margin:5px 0}
.fill-input:focus{border-color:#1a73e8;outline:none}
.fill-input.correct{border-color:#2e7d32;background:#e8f5e9}
.fill-input.wrong{border-color:#c62828;background:#ffebee}
.tf-group{display:flex;gap:8px;margin:6px 0}
.tf-btn{flex:1;padding:7px;border:2px solid #e0e0e0;border-radius:6px;text-align:center;font-size:14px;font-weight:700;cursor:pointer}
.tf-btn:hover{border-color:#90caf9}
.tf-btn.selected-true{border-color:#2e7d32;background:#e8f5e9;color:#2e7d32}
.tf-btn.selected-false{border-color:#c62828;background:#ffebee;color:#c62828}
.feedback{margin-top:6px;padding:8px 12px;border-radius:6px;display:none;font-size:12px;line-height:1.4}
.feedback.show{display:block}
.feedback.correct-fb{background:#e8f5e9;border-left:4px solid #2e7d32}
.feedback.wrong-fb{background:#ffebee;border-left:4px solid #c62828}
.feedback .ans{font-weight:700;color:#1a73e8}
.back-to-top{position:fixed;bottom:30px;right:30px;width:44px;height:44px;border-radius:50%;background:#1a73e8;color:#fff;border:none;font-size:20px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.2);display:none;z-index:999;transition:.2s}
.back-to-top:hover{background:#1557b0;transform:translateY(-2px)}
.save-btn{background:#34a853;color:#fff}
.save-btn:hover{background:#2d9249}
.header-bar{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.save-toast{position:fixed;top:20px;right:20px;background:#34a853;color:#fff;padding:12px 20px;border-radius:8px;font-size:13px;z-index:9999;opacity:0;transition:opacity .3s;pointer-events:none}
.save-toast.show{opacity:1}
.bottom-nav{display:flex;justify-content:space-between;align-items:center;margin-top:20px;padding:16px 0;border-top:1px solid #e0e0e0;gap:12px}
.bottom-nav button{padding:10px 24px;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;transition:.2s;background:#1a73e8;color:#fff;white-space:nowrap}
.bottom-nav button:hover{background:#1557b0}
.bottom-nav button:disabled{background:#ccc;cursor:not-allowed}
.bottom-nav .nav-label{font-size:13px;color:#888;text-align:center;flex:1}
.music-btn{position:fixed;bottom:90px;right:30px;width:44px;height:44px;border-radius:50%;background:#9c27b0;color:#fff;border:none;font-size:18px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.2);z-index:999;transition:.2s}
.music-btn:hover{background:#7b1fa2;transform:translateY(-2px)}
.music-btn.playing{background:#e91e63;animation:pulse 2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(233,30,99,.4)}70%{box-shadow:0 0 0 12px rgba(233,30,99,0)}100%{box-shadow:0 0 0 0 rgba(233,30,99,0)}}
.music-menu{position:fixed;bottom:140px;right:30px;background:#fff;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,.15);padding:12px;z-index:999;display:none;min-width:200px}
.music-menu.show{display:block}
.music-menu .track{display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:8px;cursor:pointer;font-size:13px;transition:.15s}
.music-menu .track:hover{background:#f5f5f5}
.music-menu .track.active{background:#f3e5f5;color:#9c27b0;font-weight:600}
.music-menu .track .indicator{width:8px;height:8px;border-radius:50%;background:#ccc}
.music-menu .track.active .indicator{background:#9c27b0}
</style>
</head>
<body>
<div class="container">
<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
<h1>西部计划 · 时政与常识测试题</h1>
<button class="tab-btn save-btn" onclick="saveProgress()">保存进度</button>
</div>
<p class="subtitle">共TOPIC_COUNT个专题，点击选择/输入答案后自动判断对错，显示正确答案</p>
<div class="tabs" id="tabHeaders"></div>
<div class="controls">
<button class="btn-reset" onclick="resetAll()">&#x21BB; 一键重置</button>
<button class="btn-show-all" onclick="showAllAnswers()">&#x1F441; 显示所有答案</button>
<button class="btn-hide-all" onclick="hideAllAnswers()">&#x1F648; 隐藏所有答案</button>
</div>
<div id="stats" class="stats"></div>
<div id="tabContent"></div>
<div class="bottom-nav">
<button id="prevBtn" onclick="prevTab()">上一页</button>
<span class="nav-label" id="navLabel">1 / TOPIC_COUNT</span>
<button id="nextBtn" onclick="nextTab()">下一页</button>
</div>
<div id="saveToast" class="save-toast">进度已保存</div>
<button class="back-to-top" id="backToTop" onclick="scrollToTop()">↑</button>
<button class="music-btn" id="musicBtn" onclick="toggleMusicMenu()">♪</button>
<div class="music-menu" id="musicMenu">
<div class="track" data-track="0" onclick="playTrack(0)">
 <span class="indicator"></span>
 <span>高山流水（古筝）</span>
</div>
<div class="track" data-track="1" onclick="playTrack(1)">
 <span class="indicator"></span>
 <span>我是奶龙 🐉</span>
</div>
</div>
<audio id="audioPlayer" loop></audio>
<script>
var allTopics = TOPICS_DATA;
var letters = ['A','B','C','D','E','F','G','H','I','J','K','L'];
var state = {};
var showAll = false;

function initState(){state={};for(var t=0;t<allTopics.length;t++){state[t]={};for(var q=0;q<allTopics[t].questions.length;q++)state[t][q]={}}}

function buildAllHTML(){
 var th='',tc='';
 for(var t=0;t<allTopics.length;t++){
  var tp=allTopics[t],a=t===0?' active':'';
  th+='<button class="tab-btn'+a+'" onclick="switchTab('+t+')">'+tp.name+'<br><small>('+tp.questions.length+'题)</small></button>';
  tc+='<div class="tab-content'+a+'" id="tab-'+t+'">';
  for(var q=0;q<tp.questions.length;q++){
   var qd=tp.questions[q];
   tc+='<div class="question-card" id="card-'+t+'-'+q+'"><div class="q-header"><span class="q-number">'+(q+1)+'</span>'+qd.q+'</div>';
   if(qd.type==='choice'&&qd.opts&&qd.opts.length>0){
    tc+='<div class="options">';
    for(var oi=0;oi<qd.opts.length;oi++){
     tc+='<div class="option" onclick="selectChoice('+t+','+q+','+oi+')" data-idx="'+oi+'"><span class="option-letter">'+letters[oi]+'</span><span>'+qd.opts[oi]+'</span></div>';
    }
    tc+='</div>';
    tc+='<div class="feedback" data-qid="'+t+'-'+q+'"><div><span class="ans"></span></div></div>';
   }else if(qd.type==='fill'){
    tc+='<input class="fill-input" type="text" placeholder="请输入答案..." oninput="checkFill('+t+','+q+',this.value)" data-qid="'+t+'-'+q+'">';
    tc+='<div class="feedback" data-qid="'+t+'-'+q+'"><div><span class="ans"></span></div></div>';
   }else{
    tc+='<div class="tf-group"><div class="tf-btn" onclick="selectJudge('+t+','+q+',true)">正确</div><div class="tf-btn" onclick="selectJudge('+t+','+q+',false)">错误</div></div>';
    tc+='<div class="feedback" data-qid="'+t+'-'+q+'"><div><span class="ans"></span></div></div>';
   }
   tc+='</div>';
  }
  tc+='</div>';
 }
 document.getElementById('tabHeaders').innerHTML=th;
 document.getElementById('tabContent').innerHTML=tc;
}

function updateQuestionUI(t, q){
 var qd=allTopics[t].questions[q];
 var qst=state[t][q]||{};
 var sel=qst.sel, val=qst.val;
 var card=document.getElementById('card-'+t+'-'+q);
 if(!card) return;

 // Update choice options
 if(qd.type==='choice'&&qd.opts&&qd.opts.length>0){
  var opts=card.querySelectorAll('.option');
  for(var oi=0;oi<opts.length;oi++){
   var cls='option';
   if(sel!==undefined||showAll){
    if(oi===qd.ans)cls+=' correct';
    if(sel===oi&&oi!==qd.ans)cls+=' wrong';
    if(sel===oi)cls+=' selected';
   }
   opts[oi].className=cls;
  }
 }

 // Update fill input
 if(qd.type==='fill'){
  var inp=card.querySelector('.fill-input');
  if(inp){
   var ic='fill-input';
   if(val!==undefined&&val.trim()!=='')ic+=(val.trim()===qd.ans.trim())?' correct':' wrong';
   inp.className=ic;
  }
 }

 // Update feedback
 var fb=card.querySelector('.feedback');
 if(fb){
  var showFb=(sel!==undefined||showAll)&&(qd.type!=='fill'||(val!==undefined&&val.trim()!==''));
  var isCorrect=false;
  if(qd.type==='fill'){isCorrect=val!==undefined&&val.trim()!==''&&val.trim()===qd.ans.trim();}
  else{isCorrect=sel!==undefined&&sel===qd.ans;}
  if(showAll&&sel===undefined&&qd.type!=='fill'){isCorrect=true;showFb=true;}
  if(showAll&&qd.type==='fill'&&(val===undefined||val.trim()==='')){showFb=false;}

  if(showFb){
   fb.className='feedback show '+(isCorrect?'correct-fb':'wrong-fb');
   var ansSpan=fb.querySelector('.ans');
   if(qd.type==='fill'){
    ansSpan.textContent='正确答案：'+qd.ans;
   }else if(qd.opts&&qd.opts.length>0){
    ansSpan.textContent='正确答案：'+letters[qd.ans]+'. '+qd.opts[qd.ans];
   }else{
    ansSpan.textContent='正确答案：'+(qd.ans?'正确':'错误');
   }
  }else{
   fb.className='feedback';
  }
 }

 updateStats();
}

function updateStats(){
 var total=0,correct=0,wrong=0,unans=0;
 for(var t=0;t<allTopics.length;t++)for(var q=0;q<allTopics[t].questions.length;q++){
  var qd=allTopics[t].questions[q],qst=state[t][q]||{},sel=qst.sel,val=qst.val;
  total++;
  if(qd.type==='fill'){
   if(val===undefined||val.trim()==='')unans++;
   else if(val.trim()===qd.ans.trim())correct++;
   else wrong++;
  }else{
   if(sel===undefined)unans++;
   else if(sel===qd.ans)correct++;
   else wrong++;
  }
 }
 var pct=total>0?((correct/total)*100).toFixed(1):0;
 document.getElementById('stats').innerHTML='<div class="stat-item">总题数：<span>'+total+'</span></div><div class="stat-item">正确：<span style="color:#2e7d32">'+correct+'</span></div><div class="stat-item">错误：<span style="color:#c62828">'+wrong+'</span></div><div class="stat-item">未答：<span style="color:#888">'+unans+'</span></div><div class="stat-item">正确率：<span>'+pct+'%</span></div>';
}

function selectChoice(t,q,oi){
 if(!state[t][q])state[t][q]={};
 state[t][q].sel=oi;
 updateQuestionUI(t,q);
}

function checkFill(t,q,val){
 if(!state[t][q])state[t][q]={};
 state[t][q].val=val;
 // Only re-render the specific question, not full page
 updateQuestionUI(t,q);
}

function selectJudge(t,q,val){
 if(!state[t][q])state[t][q]={};
 state[t][q].sel=val;
 updateQuestionUI(t,q);
}

var currentTab=0;

function switchTab(t){
 currentTab=t;
 var tabs=document.querySelectorAll('.tab-content'),btns=document.querySelectorAll('.tab-btn');
 for(var i=0;i<tabs.length;i++)tabs[i].classList.remove('active');
 for(var i=0;i<btns.length;i++)btns[i].classList.remove('active');
 document.getElementById('tab-'+t).classList.add('active');btns[t].classList.add('active');
 var total=allTopics.length;
 document.getElementById('navLabel').textContent=(t+1)+' / '+total;
 document.getElementById('prevBtn').disabled=(t===0);
 document.getElementById('nextBtn').disabled=(t===total-1);
}

function prevTab(){if(currentTab>0)switchTab(currentTab-1);}
function nextTab(){if(currentTab<allTopics.length-1)switchTab(currentTab+1);}

function resetAll(){
 if(!confirm('确定要重置所有答案吗？'))return;
 initState();
 showAll=false;
 // Rebuild HTML to reset all UI
 buildAllHTML();
 updateStats();
}

function showAllAnswers(){
 showAll=true;
 // Update all question cards
 for(var t=0;t<allTopics.length;t++)for(var q=0;q<allTopics[t].questions.length;q++)updateQuestionUI(t,q);
}

function hideAllAnswers(){
 showAll=false;
 for(var t=0;t<allTopics.length;t++)for(var q=0;q<allTopics[t].questions.length;q++)updateQuestionUI(t,q);
}

// Music player
var currentTrack=0;
var isPlaying=false;

var tracks=[
 {name:'高山流水（古筝）',url:'guzheng.mp3'},
 {name:'我是奶龙 🐉',url:'nailong.mp3'}
];

function toggleMusicMenu(){
 var menu=document.getElementById('musicMenu');
 menu.classList.toggle('show');
}

function playTrack(idx){
 var player=document.getElementById('audioPlayer');
 var btn=document.getElementById('musicBtn');
 var menuItems=document.querySelectorAll('.music-menu .track');

 if(currentTrack===idx && isPlaying){
  player.pause();
  isPlaying=false;
  btn.classList.remove('playing');
  btn.textContent='♪';
  document.getElementById('musicMenu').classList.remove('show');
  return;
 }

 currentTrack=idx;
 btn.textContent='⏳';
 btn.disabled=true;
 for(var i=0;i<menuItems.length;i++)menuItems[i].classList.remove('active');

 player.src=tracks[idx].url;
 player.load();

 var playWhenReady=function(){
  player.play().then(function(){
   isPlaying=true;
   btn.classList.add('playing');
   btn.textContent='♫';
   btn.disabled=false;
   document.querySelector('.music-menu .track[data-track="'+idx+'"]').classList.add('active');
   document.getElementById('musicMenu').classList.remove('show');
  }).catch(function(e){
   btn.textContent='♪';
   btn.disabled=false;
   alert('无法播放 '+tracks[idx].name+'。请确认mp3文件与HTML在同一目录下。错误：'+e.message);
  });
 };

 if(player.readyState>=2){playWhenReady();}
 else{
  player.addEventListener('canplay',playWhenReady,{once:true});
  setTimeout(function(){if(!isPlaying&&btn.textContent==='⏳')playWhenReady();},3000);
 }
}

document.addEventListener('click',function(e){
 if(!e.target.closest('.music-btn') && !e.target.closest('.music-menu')){
  document.getElementById('musicMenu').classList.remove('show');
 }
});

// Scroll to top button
window.addEventListener('scroll',function(){
 var btn=document.getElementById('backToTop');
 if(btn)btn.style.display=(window.scrollY>300)?'block':'none';
});
function scrollToTop(){window.scrollTo({top:0,behavior:'smooth'});}

// Save progress to localStorage
function saveProgress(){
 try{
  var saveData={};
  for(var t=0;t<allTopics.length;t++){
   saveData[t]={};
   for(var q=0;q<allTopics[t].questions.length;q++){
    var qst=state[t][q]||{};
    if(qst.sel!==undefined||(qst.val!==undefined&&qst.val.trim()!=='')){
     saveData[t][q]={};
     if(qst.sel!==undefined)saveData[t][q].sel=qst.sel;
     if(qst.val!==undefined&&qst.val.trim()!=='')saveData[t][q].val=qst.val;
    }
   }
  }
  localStorage.setItem('xibu_quiz_progress',JSON.stringify(saveData));
  var toast=document.getElementById('saveToast');
  if(toast){toast.classList.add('show');setTimeout(function(){toast.classList.remove('show');},2000);}
 }catch(e){alert('保存失败：'+e.message);}
}

// Load progress from localStorage
function loadProgress(){
 try{
  var saved=localStorage.getItem('xibu_quiz_progress');
  if(!saved)return;
  var saveData=JSON.parse(saved);
  for(var t in saveData){
   if(!state[t])state[t]={};
   for(var q in saveData[t]){
    if(!state[t][q])state[t][q]={};
    if(saveData[t][q].sel!==undefined)state[t][q].sel=saveData[t][q].sel;
    if(saveData[t][q].val!==undefined)state[t][q].val=saveData[t][q].val;
   }
  }
 }catch(e){/* ignore */ }
}

initState();
loadProgress();
buildAllHTML();
updateStats();
</script>
</div>
</body>
</html>'''

html = HTML.replace('TOPICS_DATA', topics_json)
html = html.replace('TOPIC_COUNT', str(len(topics)))

outpath = os.path.join(DIR, '西部计划_测试题.html')
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'\nHTML generated: {outpath}')
print(f'File size: {os.path.getsize(outpath)} bytes')
