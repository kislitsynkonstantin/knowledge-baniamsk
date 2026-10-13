# -*- coding: utf-8 -*-
"""Проба главной: разделы «Ведомостью» — из базы, а не из разметки.

Константин 13.10.2026, снимком варианта 01 макета kb-sections-v2: «А список
уроков вот эту внедряй Ведомость».

Держит, на 1440 (меню закреплено), 1000, 768 и 390 px, днём и ночью:
  • разделы — все блоки из базы по порядку: крупный бледный номер, название,
    «N уроков · не начат / пройден 1 / пройдено N / пройдены все», процент
    справа и линия пройденного под строкой; пустой блок — «Уроки готовятся»,
    «Скоро» и пунктир вместо линии, на нажатие не отвечает;
  • названия блоков и число уроков в исходнике страницы не стоят: прежде
    плитки с ними лежали в разметке, а числа не обновлялись вовсе;
  • сверху общий счёт «2 из 15 пройдено» и полоса той же доли;
  • нажатие и Enter открывают раздел; отметка урока и возврат на главную
    сдвигают счёт; язык переключается без перерисовки;
  • ничего не вылезает и не обрезано, строка на телефоне не ниже 44 px,
    процент не прилипает к краю.

Шрифты — настоящие (шрифты_google.css калькулятора).

Запуск: python3 scratchpad/probes/check_kb_home_list.py (из корня репозитория).
"""
import json, os, pathlib, threading, http.server, socketserver, functools, sys
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get('BM_KB') or '/home/user/knowledge-baniamsk')
ЗДЕСЬ = pathlib.Path(__file__).parent
ШРИФТЫ = pathlib.Path(os.environ.get('BM_FONTS_CSS') or '/home/user/-calculator-test/scratchpad/probes/шрифты_google.css')
зам, отч = [], []
def факт(у, т): (отч if у else зам).append(("    ок  " if у else "") + т)

# Имена блоков — из базы; в исходнике их быть не должно.
исходник = (КОРЕНЬ / 'index.html').read_text(encoding='utf-8')
следы = [с for с in ('>Компания<', '>Продукт<', '>Продажи<', '>Конкуренты<', '>Для клиентов<', '11 уроков', '2 урока') if с in исходник]
факт(not следы, f"в исходнике нет имён блоков и числа уроков: {следы or 'чисто'}")


def урок(б, о, статус='ready'):
    return dict(id=f'lesson-{б}-{о}', block=б, ord=о, status=статус, title_ru=f'Урок {б}.{о}', title_en=f'Lesson {б}.{о}',
                nav_ru=f'Урок {б}.{о}', nav_en=f'Lesson {б}.{о}', sub_ru='', sub_en='',
                body_html='' if статус == 'planned' else f'<div id="lesson-{б}-{о}"><h2>Урок {б}.{о}</h2></div>')


УРОКИ = [урок(1, 1, 'planned'), урок(1, 3), урок(1, 9)] + [урок(3, и) for и in range(1, 12)] + [урок(5, 1), урок(5, 2)]
БЛОКИ = [dict(id='b1', num=1, ord=1, name_ru='Компания', name_en='Company', sub_ru='', sub_en=''),
         dict(id='b2', num=2, ord=2, name_ru='Продукт', name_en='Product', sub_ru='', sub_en=''),
         dict(id='b3', num=3, ord=3, name_ru='Продажи', name_en='Sales', sub_ru='', sub_en=''),
         dict(id='b4', num=4, ord=4, name_ru='Конкуренты', name_en='Competitors', sub_ru='', sub_en=''),
         dict(id='b5', num=5, ord=5, name_ru='Для клиентов', name_en='For clients', sub_ru='', sub_en='')]
ПРОЙДЕНО = ['3.1', '5.1']

ЗАГЛУШКА = """
window.__уроки = %s; window.__блоки = %s; window.__пройдено = %s;
const _сессия = { user: { id: 'u1', email: 'm@baniamsk.ru' }, access_token: 't' };
window.supabase = { createClient: () => ({
  auth: {
    getSession: async () => ({ data: { session: _сессия } }),
    onAuthStateChange: () => ({ data: { subscription: { unsubscribe(){} } } }),
    signInWithPassword: async () => ({ data: { session: _сессия }, error: null }),
    setSession: async () => ({ data: { session: _сессия }, error: null }),
    signOut: async () => ({})
  },
  from: (имя) => {
    const данные = имя === 'kb_lessons' ? window.__уроки
                 : имя === 'kb_blocks'  ? window.__блоки
                 : имя === 'kb_lesson_progress' ? window.__пройдено.map(л => ({ user_id: 'u1', lesson_id: л, status: 'completed' }))
                 : имя === 'profiles'   ? [{ id:'u1', email:'m@baniamsk.ru', full_name:'Проба', role:'manager' }]
                 : [];
    const ответ = { data: данные, error: null };
    const цепь = {
      select: () => цепь, order: () => цепь, eq: () => цепь, is: () => цепь, in: () => цепь,
      maybeSingle: async () => ({ data: данные[0] || null, error: null }),
      single: async () => ({ data: данные[0] || null, error: null }),
      then: (ф, о) => Promise.resolve(ответ).then(ф, о)
    };
    return { select: () => цепь, upsert: async () => ({ error: null }), update: () => цепь, insert: async () => ({ error: null }) };
  }
}) };
""" % (json.dumps(УРОКИ, ensure_ascii=False), json.dumps(БЛОКИ, ensure_ascii=False), json.dumps(ПРОЙДЕНО))

ВИД = """() => {
  const вид = э => !!э && э.getClientRects().length > 0 && getComputedStyle(э).display !== 'none' && getComputedStyle(э).visibility !== 'hidden';
  const экр = document.querySelector('#homeScreen .hs-wrap'), w = innerWidth;
  const строки = [...document.querySelectorAll('#hsList > li')];
  const т = (э, с) => { const х = э.querySelector(с); return х && вид(х) ? х.innerText.replace(/\\s+/g, ' ').trim() : ''; };
  const видимые = [...экр.querySelectorAll('*')].filter(вид);
  return {
    открыт: вид(экр),
    счёт: ((document.getElementById('hsProgLabel') || {}).innerText || '').replace(/\\s+/g, ' ').trim(),
    полоса: (document.getElementById('hsProgFill') || {}).style?.width || '',
    строк: строки.length,
    номера: строки.map(р => т(р, '.hs-no')), имена: строки.map(р => т(р, '.hs-nm')),
    подписи: строки.map(р => т(р, '.hs-meta')), проценты: строки.map(р => т(р, '.hs-pct')),
    скоро: строки.map(р => т(р, '.hs-tag')), пусто: строки.map(р => р.classList.contains('wip')),
    // Число и знак процента — одним куском текста: отдельными частями гибкого
    // ряда их разносит зазор ряда, и «9  %» читается как два значения.
    слитно: строки.filter(р => р.querySelector('.hs-pct')).every(р => { const п = р.querySelector('.hs-pct'), к = п.firstElementChild;
      return к && к.tagName !== 'svg' && /\d/.test(к.innerText) && /%/.test(к.innerText) && ![...п.childNodes].some(у => у.nodeType === 3 && у.textContent.trim()); }),
    линии: строки.map(р => { const и = р.querySelector('.hs-line i'); return и ? и.style.width : ''; }),
    фокус: строки.map(р => р.tabIndex),
    вылез: видимые.filter(э => { const б = э.getBoundingClientRect(); return б.width && (б.right > w + .5 || б.left < -.5); }).map(э => э.className || э.tagName).slice(0, 5),
    обрез: видимые.filter(э => /hs-(nm|meta|pct|tag|prog-label)/.test(э.className) && э.scrollWidth > э.clientWidth + 1).map(э => э.className).slice(0, 5),
    вширь: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    высота: строки.length ? Math.min(...строки.map(р => Math.round(р.getBoundingClientRect().height))) : 0,
    правый: строки.length ? Math.min(...строки.map(р => { const п = р.querySelector('.hs-pct, .hs-tag'); return п ? Math.round(р.getBoundingClientRect().right - п.getBoundingClientRect().right) : 99; })) : 0,
    шрифт: (() => { const с = document.createElement('span'); с.textContent = 'Продажи 0123'; с.style.cssText = 'position:absolute;font:700 40px Unbounded,monospace';
      document.body.appendChild(с); const а = с.getBoundingClientRect().width; с.style.fontFamily = 'monospace'; const б = с.getBoundingClientRect().width; с.remove(); return Math.round(а - б); })()
  };
}"""


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а): pass


socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
порт = с.server_address[1]
хром = os.environ.get('BM_CHROMIUM') or str(sorted(pathlib.Path('/opt/pw-browsers').glob('chromium-*/chrome-linux/chrome'))[-1])
css = ШРИФТЫ.read_text(encoding='utf-8')
ошибки = []


def открыть(бр, ш, в, схема):
    стр = бр.new_page(viewport={"width": ш, "height": в}, color_scheme=схема, device_scale_factor=2 if ш == 1440 else 1)
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=css))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    стр.add_init_script(ЗАГЛУШКА)
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.goto(f"http://127.0.0.1:{порт}/", wait_until="load"); стр.wait_for_timeout(2200)
    стр.evaluate("() => { if (window.innerWidth > 880 && typeof pinSidebar === 'function') try { pinSidebar(); } catch (e) {} showHomeScreen(); }")
    стр.wait_for_timeout(500)
    return стр


with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    for ш, в in ((1440, 900), (1000, 800), (768, 1000), (390, 844)):
        for схема in ('light', 'dark'):
            н = f"[{ш} {'день' if схема == 'light' else 'ночь'}]"
            стр = открыть(бр, ш, в, схема)
            д = стр.evaluate(ВИД)
            if ш == 1440 and схема == 'light':
                факт(д['шрифт'] != 0, f"{н} Unbounded лёг, а не подменён: разница ширины {д['шрифт']} px")
            факт(д['открыт'] and д['счёт'] == '2 из 15 пройдено' and д['полоса'] == '13%', f"{н} общий счёт и полоса: {д['счёт']!r}, {д['полоса']!r}")
            факт(д['строк'] == 5 and д['номера'] == ['01', '02', '03', '04', '05'], f"{н} пять разделов по порядку: {д['номера']}")
            факт(д['имена'] == ['Компания', 'Продукт', 'Продажи', 'Конкуренты', 'Для клиентов'], f"{н} имена из базы: {д['имена']}")
            факт(д['подписи'] == ['2 урока · не начат', 'Уроки готовятся', '11 уроков · пройден 1', 'Уроки готовятся', '2 урока · пройден 1'],
                 f"{н} подписи: {д['подписи']}")
            факт(д['проценты'] == ['0 %', '', '9 %', '', '50 %'] and д['линии'] == ['0%', '', '9%', '', '50%'], f"{н} проценты и линии: {д['проценты']}, {д['линии']}")
            факт(д['слитно'], f"{н} число и знак процента — одним куском: {д['слитно']}")
            факт(д['пусто'] == [False, True, False, True, False] and [x.lower() for x in д['скоро']] == ['', 'скоро', '', 'скоро', ''],
                 f"{н} пустые блоки — «Скоро»: {д['пусто']}, {д['скоро']}")
            факт(д['фокус'] == [0, -1, 0, -1, 0], f"{н} фокус клавиатурой — только у раскрываемых разделов: {д['фокус']}")
            факт(not д['вылез'] and д['вширь'] <= 0 and not д['обрез'], f"{н} ничего не вылезает и не обрезано: {д['вылез']}, вширь {д['вширь']}, {д['обрез']}")
            if ш in (768, 390):
                факт(д['высота'] >= 44, f"{н} строка не ниже 44 px: {д['высота']}")
            факт(д['правый'] >= 2, f"{н} процент не прилипает к краю: {д['правый']} px")
            стр.screenshot(path=str(ЗДЕСЬ / f"главная-{ш}-{схема}.png"), full_page=ш != 1440)
            if ш == 1440 and схема == 'light' and д['строк'] == 5:
                стр.click('#hsList > li:nth-child(2)'); стр.wait_for_timeout(300)
                о = стр.evaluate("() => getComputedStyle(document.getElementById('sectionScreen')).display")
                факт(о == 'none', f"{н} пустой блок на нажатие не отвечает: экран раздела {о}")
                стр.click('#hsList > li:nth-child(3)'); стр.wait_for_timeout(400)
                о = стр.evaluate("() => [getComputedStyle(document.getElementById('sectionScreen')).display, document.getElementById('secTag').innerText]")
                факт(о[0] == 'block' and '03' in о[1], f"{н} нажатие на «Продажи» открыло раздел: {о}")
                стр.evaluate("() => { toggleComplete('3.2'); showHomeScreen(); }"); стр.wait_for_timeout(400)
                д2 = стр.evaluate(ВИД)
                факт(д2['счёт'] == '3 из 15 пройдено' and д2['подписи'][2] == '11 уроков · пройдено 2' and д2['проценты'][2] == '18 %',
                     f"{н} отметка урока и возврат сдвинули счёт: {д2['счёт']!r}, {д2['подписи'][2]!r}, {д2['проценты'][2]!r}")
                стр.focus('#hsList > li:nth-child(5)'); стр.keyboard.press('Enter'); стр.wait_for_timeout(400)
                о = стр.evaluate("() => [getComputedStyle(document.getElementById('sectionScreen')).display, document.getElementById('secTag').innerText]")
                факт(о[0] == 'block' and '05' in о[1], f"{н} Enter на «Для клиентов» открыл раздел: {о}")
                стр.evaluate("() => { showHomeScreen(); setLang('en'); }"); стр.wait_for_timeout(300)
                д3 = стр.evaluate(ВИД)
                факт(д3['счёт'] == '3 of 15 completed' and д3['имена'][0] == 'Company' and д3['подписи'][0] == '2 lessons · not started'
                     and д3['подписи'][2] == '11 lessons · 2 completed' and д3['скоро'][1].lower() == 'soon' and д3['проценты'][2] == '18%',
                     f"{н} английский без перерисовки: {д3['счёт']!r}, {д3['имена'][:1]}, {д3['подписи'][:3]}, {д3['скоро'][1]!r}, {д3['проценты'][2]!r}")
                стр.evaluate("() => setLang('ru')")
            стр.close()
    бр.close()
с.shutdown()
важные = [о for о in ошибки if 'favicon' not in о]
факт(not важные, f"ошибок страницы нет: {важные[:2]}")
print("\n".join(отч))
if зам:
    print("НАХОДКИ:"); [print("  ✗", з) for з in зам]; sys.exit(1)
print("Чисто: главная — разделы «Ведомостью» из базы, на 1440/1000/768/390 днём и ночью; нажатие, Enter, отметка и язык работают.")
