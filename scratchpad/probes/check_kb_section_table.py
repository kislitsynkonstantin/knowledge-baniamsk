# -*- coding: utf-8 -*-
"""Проба экрана раздела: уроки таблицей, полоса уроков сверху.

Константин 13.10.2026, снимками макета kb-lessons-blank-v1: «Внедряй 5 вариант
таблица. Только вот эту полоску сверху с плитками уроков добавь».

Держит, на 1440 (меню закреплено), 1000 (меню закреплено, колонка узкая),
768 и 390 px, днём и ночью, в «Зелёном-графите» (база по своей ссылке):
  • сверху «Блок 03» и счёт «5 из 11», под ними полоса — по клетке на урок:
    залиты пройденные, обведена следующая (первая непройденная по порядку);
  • таблица: строка на урок, номер, название, «О чём» — отдельной колонкой
    там, где колонка шире 620 px, иначе подписью под названием; состояние:
    «Пройден» словом, без галочки, «Дальше», «Не начат» (на узкой — «Пройден»
    и «Дальше», «Не начат» молчит); внизу «Пройдено — 5 из 11 · 45 %»;
    Константин 13.10.2026: «Вместо галочек напиши фразу, типа „пройдено“»;
  • следующая строка заметна на фоне страницы, а не сливается с ним;
  • ничего не вылезает за экран и не обрезано, строка на телефоне не ниже
    44 px, кнопка «Главная» ловится пальцем;
  • нажатие и Enter на строке открывают урок; переключение языка на
    открытом разделе — английские подписи без перерисовки;
  • все уроки пройдены — «Дальше» нет, полоса залита; ни одного — следующий
    первый урок.

Шрифты — настоящие (шрифты_google.css калькулятора), и проба сперва
убеждается, что Unbounded лёг, а не подменён.

Запуск: python3 scratchpad/probes/check_kb_section_table.py (из корня репозитория).
"""
import json, os, pathlib, threading, http.server, socketserver, functools, sys
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get('BM_KB') or '/home/user/knowledge-baniamsk')
ЗДЕСЬ = pathlib.Path(__file__).parent
ШРИФТЫ = pathlib.Path(os.environ.get('BM_FONTS_CSS') or '/home/user/-calculator-test/scratchpad/probes/шрифты_google.css')
зам, отч = [], []
def факт(у, т): (отч if у else зам).append(("    ок  " if у else "") + т)

# Названия придуманы: настоящее оглавление закрыто в базе.
ИМЕНА = ["Отдел продаж изнутри", "Портрет покупателя бани", "Каркас, брус, камень", "Смета без сюрпризов",
         "Звонок по заявке", "Разговор о бюджете", "Работа с возражениями", "Показ проекта на встрече",
         "Сравнение с конкурентами", "Договор и предоплата", "После подписания с длинным названием урока для переноса"]
УРОКИ = [dict(id=f'lesson-3-{и + 1}', block=3, ord=и + 1, status='ready', title_ru=и_, title_en=f'Lesson {и + 1}',
              nav_ru=и_, nav_en=f'Lesson {и + 1}', sub_ru=f'Подпись урока {и + 1}', sub_en=f'Subtitle {и + 1}',
              body_html=f'<div id="lesson-3-{и + 1}"><h2>Урок 3.{и + 1}</h2><p>Тело</p></div>')
         for и, и_ in enumerate(ИМЕНА)]
УРОКИ.append(dict(id='lesson-1-3', block=1, ord=3, status='ready', title_ru='Урок блока 1', title_en='Block 1 lesson',
                  nav_ru='Урок 1.3', nav_en='Lesson 1.3', sub_ru='', sub_en='', body_html='<div id="lesson-1-3"><h2>Урок 1.3</h2></div>'))
БЛОКИ = [dict(id='b1', num=1, ord=1, name_ru='Компания', name_en='Company', sub_ru='Кто мы', sub_en='Who we are'),
         dict(id='b3', num=3, ord=3, name_ru='Продажи', name_en='Sales', sub_ru='Как вести клиента от заявки до договора',
              sub_en='From request to contract')]
ПРОЙДЕНО = ['3.1', '3.2', '3.3', '3.4', '3.6']

ЗАГЛУШКА = """
window.__уроки = %s; window.__блоки = %s;
window.__пройдено = %s;
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
  const экр = document.getElementById('sectionScreen'), w = innerWidth;
  const клетки = [...document.querySelectorAll('#secCells > *')];
  const строки = [...document.querySelectorAll('#secLessonList tbody tr')];
  const ст = т => { const s = т.querySelector('[class*="st"]'); return s ? s.innerText.replace(/\\s+/g, ' ').trim() : ''; };
  const rgb = s => (/rgba?\\(([^)]+)\\)/.exec(s) || [0, '0,0,0'])[1].split(',').map(Number);
  const яркость = ([r, g, b]) => { const к = v => (v /= 255) <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; return .2126 * к(r) + .7152 * к(g) + .0722 * к(b); };
  // Фон строки сводится с фоном страницы на холсте: color-mix и прозрачность
  // разбором строки цвета не прочесть.
  const свести = (низ, верх) => { const х = document.createElement('canvas'); х.width = х.height = 1; const к = х.getContext('2d');
    к.fillStyle = низ; к.fillRect(0, 0, 1, 1); if (верх) { к.fillStyle = верх; к.fillRect(0, 0, 1, 1); } return [...к.getImageData(0, 0, 1, 1).data].slice(0, 3); };
  const фонТела = getComputedStyle(document.body).backgroundColor;
  const фонСтраницы = свести(фонТела);
  const след = строки.find(т => т.classList.contains('next'));
  const фонСлед = след ? свести(фонТела, getComputedStyle(след.querySelector('td')).backgroundColor) : null;
  const я1 = яркость(фонСтраницы), я2 = фонСлед ? яркость(фонСлед) : я1;
  const видимые = [...экр.querySelectorAll('*')].filter(вид);
  const вылез = видимые.filter(э => { const б = э.getBoundingClientRect(); return б.width && (б.right > w + .5 || б.left < -.5); }).map(э => э.className || э.tagName).slice(0, 5);
  const обрез = видимые.filter(э => /slr-|c-ab|sec-st|sec-count|sec-tag/.test(э.className) && э.scrollWidth > э.clientWidth + 1).map(э => э.className).slice(0, 5);
  const назадЭ = экр.querySelector('.sec-back'), назад = назадЭ.getBoundingClientRect(), пп = getComputedStyle(назадЭ, '::before');
  const доп = v => пп.content !== 'none' && пп.position === 'absolute' ? -parseFloat(v) || 0 : 0;
  const ширинаКолонки = Math.round(экр.querySelector('.sec-wrap').getBoundingClientRect().width);
  const колонка = строки[0] ? вид(строки[0].querySelector('.c-ab')) : null;
  const подпись = строки[0] ? вид(строки[0].querySelector('.slr-sub')) : null;
  const правый = строки.map(т => { const я = т.lastElementChild, с = я.firstElementChild; return с ? Math.round(я.getBoundingClientRect().right - с.getBoundingClientRect().right) : 99; });
  return {
    открыт: вид(экр), тег: (document.getElementById('secTag') || {}).innerText || '',
    счёт: ((document.getElementById('secCount') || {}).innerText || '').replace(/\\s+/g, ' ').trim(),
    клеток: клетки.length, залито: клетки.filter(к => к.classList.contains('done')).length,
    следКлетка: клетки.findIndex(к => к.classList.contains('next')),
    строк: строки.length, номера: строки.map(т => т.querySelector('.c-n').innerText.trim()),
    состояния: строки.map(ст), галочек: строки.filter(т => т.lastElementChild.querySelector('polyline')).length, следСтрока: строки.findIndex(т => т.classList.contains('next')),
    итог: ((document.querySelector('#secLessonList tfoot') || {}).innerText || '').replace(/\\s+/g, ' ').trim(),
    шапка: [...document.querySelectorAll('#secLessonList thead th')].filter(вид).map(э => э.innerText.trim()),
    видШапки: [...new Set([...document.querySelectorAll('#secLessonList thead th')].filter(вид).map(э => { const с = getComputedStyle(э); return с.fontSize + ' ' + с.fontWeight + ' ' + с.color + ' ' + с.fontFamily.split(',')[0]; }))],
    колонка, подпись, контраст: Math.round(((Math.max(я1, я2) + .05) / (Math.min(я1, я2) + .05)) * 1000) / 1000,
    вылез, обрез, вширь: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    высотаСтроки: Math.min(...строки.map(т => Math.round(т.getBoundingClientRect().height))),
    назад: [Math.round(назад.width + доп(пп.left) + доп(пп.right)), Math.round(назад.height + доп(пп.top) + доп(пп.bottom))], правый: Math.min(...правый), ширинаКолонки,
    тон: document.documentElement.dataset.tone || '',
    полоска: (() => { if (!след) return null; const я = след.querySelector('td'), с = getComputedStyle(я, '::before');
      const внутри = getComputedStyle(я).boxShadow.indexOf('inset') > -1;
      if (с.content === 'none' || с.position !== 'absolute') return { внутри, зазор: null };
      const т = я.closest('table').getBoundingClientRect(), л = я.getBoundingClientRect().left + parseFloat(с.left) + parseFloat(с.width);
      return { внутри, зазор: Math.round(т.left - л) }; })(),
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


def открыть(бр, ш, в, схема, пройдено=None):
    стр = бр.new_page(viewport={"width": ш, "height": в}, color_scheme=схема, device_scale_factor=2 if ш == 1440 else 1)
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=css))
    стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
    стр.add_init_script(ЗАГЛУШКА + (f"window.__пройдено = {json.dumps(пройдено)};" if пройдено is not None else ""))
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.goto(f"http://127.0.0.1:{порт}/", wait_until="load"); стр.wait_for_timeout(2200)
    стр.evaluate("() => { if (window.innerWidth > 880 && typeof pinSidebar === 'function') try { pinSidebar(); } catch (e) {} openSection('b3'); }")
    стр.wait_for_timeout(700)
    return стр


with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    for ш, в in ((1440, 900), (1000, 800), (768, 1000), (390, 844)):
        for схема in ('light', 'dark'):
            н = f"[{ш} {'день' if схема == 'light' else 'ночь'}]"
            стр = открыть(бр, ш, в, схема)
            д = стр.evaluate(ВИД)
            широкая = д['колонка']
            if ш == 1440 and схема == 'light':
                факт(д['шрифт'] != 0, f"{н} Unbounded лёг, а не подменён: разница ширины {д['шрифт']} px")
                факт(д['тон'] == 'bmsk', f"{н} база по своей ссылке — «Зелёный-графит»: {д['тон']!r}")
            факт(д['открыт'], f"{н} экран раздела открыт")
            факт(д['тег'].strip().lower() == 'блок 03' and д['счёт'] == '5 из 11', f"{н} сверху «Блок 03» и «5 из 11»: {д['тег']!r}, {д['счёт']!r}")
            факт(д['клеток'] == 11 and д['залито'] == 5 and д['следКлетка'] == 4, f"{н} полоса: 11 клеток, 5 залиты, обведена 5-я: {д['клеток']}, {д['залито']}, {д['следКлетка']}")
            факт(д['строк'] == 11 and д['номера'][:2] == ['3.1', '3.2'] and д['номера'][-1] == '3.11', f"{н} строк 11, номера по порядку: {д['номера'][:3]}…{д['номера'][-1:]}")
            факт(д['следСтрока'] == 4, f"{н} «Дальше» — у 3.5, первой непройденной: строка {д['следСтрока']}")
            ждём = (['Пройден'] * 4 + ['Дальше', 'Пройден'] + ['Не начат'] * 5) if широкая else (['Пройден'] * 4 + ['Дальше', 'Пройден'] + [''] * 5)
            факт(д['состояния'] == ждём, f"{н} состояния ({'широкая' if широкая else 'узкая'} колонка): {д['состояния']}")
            факт(д['галочек'] == 0, f"{н} пройденный урок — словом, галочек нет: {д['галочек']}")
            факт(д['итог'].startswith('Пройдено') and '5 из 11' in д['итог'] and '45 %' in д['итог'], f"{н} итог внизу: {д['итог']!r}")
            # «О чём» колонкой ровно там, где колонка раздела не уже 620 px.
            факт(широкая == (д['ширинаКолонки'] >= 620) and д['подпись'] == (not широкая), f"{н} колонка раздела {д['ширинаКолонки']} px: «О чём» {'колонкой' if широкая else 'под названием'}")
            if ш == 1440:
                факт(широкая and [х.lower() for х in д['шапка']] == ['№', 'урок', 'о чём', 'состояние'], f"{н} шапка: {д['шапка']}")
            if ш == 1000:
                факт(not широкая, f"{н} меню закреплено, колонка узкая — «О чём» под названием: {д['ширинаКолонки']} px")
            if ш in (768, 390):
                факт(д['высотаСтроки'] >= 44, f"{н} строка не ниже 44 px: {д['высотаСтроки']}")
            факт(len(д['видШапки']) == 1, f"{н} заголовки колонок одного вида: {д['видШапки']}")
            п = д['полоска']
            # Черты в выделении нет нигде (Константин 18.10.2026): следующий урок —
            # только заливкой строки, ни полоски левее таблицы, ни inset-тени.
            факт(п is None or (not п['внутри'] and п['зазор'] is None), f"{н} у следующего урока черта слева: {п}")
            факт(д['контраст'] >= 1.04, f"{н} следующая строка заметна на фоне страницы: {д['контраст']}:1")
            if ш == 1440 and схема == 'light':
                # Открытый урок в меню и пункт оглавления урока — тоже без черты
                # слева, ни рамкой, ни inset-тенью, во всех состояниях (Константин
                # 19.10.2026: «1 — да»). Правила читаются из самих стилей страницы.
                черты = стр.evaluate(r"""() => { const н = [];
                  for (const лист of document.styleSheets) { let пр; try { пр = лист.cssRules; } catch (e) { continue; }
                    for (const п of пр) { if (!п.selectorText || !/\.sb-a|side-nav-item|sec-tb tr\.next/.test(п.selectorText)) continue;
                      const с = п.style, ш_ = с.borderLeftWidth, цв = с.borderLeftColor, т = с.boxShadow || '';
                      if ((ш_ && parseFloat(ш_) > 0 && с.borderLeftStyle !== 'none') || (цв && цв !== 'transparent') || /inset\s+[1-9]/.test(т)
                          || (/::before|::after/.test(п.selectorText) && parseFloat(с.width) > 0 && parseFloat(с.width) <= 4))
                        н.push(п.selectorText); } }
                  return н; }""")
                факт(not черты, f"{н} черты слева у меню, оглавления урока и следующего урока нет: {черты}")
            факт(not д['вылез'] and д['вширь'] <= 0 and not д['обрез'], f"{н} ничего не вылезает и не обрезано: {д['вылез']}, вширь {д['вширь']}, {д['обрез']}")
            факт(min(д['назад']) >= 32, f"{н} «Главная» ловится: {д['назад']}")
            факт(д['правый'] >= 6, f"{н} состояние не прилипает к правому краю строки: {д['правый']} px")
            стр.screenshot(path=str(ЗДЕСЬ / f"раздел-{ш}-{схема}.png"), full_page=ш != 1440)
            if ш == 1440 and схема == 'light' and д['строк'] < 7:
                факт(False, f"{н} строк таблицы нет — нажатие и язык проверить не на чем")
            elif ш == 1440 and схема == 'light':
                # нажатие и Enter
                стр.click('#secLessonList tbody tr:nth-child(7)'); стр.wait_for_timeout(300)
                о = стр.evaluate("() => ({ урок: (document.getElementById('lesson-3-7') || {}).style?.display, раздел: getComputedStyle(document.getElementById('sectionScreen')).display })")
                факт(о['урок'] == 'block', f"{н} нажатие на строку 3.7 открыло урок: {о}")
                стр.evaluate("() => openSection('b3')"); стр.wait_for_timeout(300)
                стр.focus('#secLessonList tbody tr:nth-child(2)'); стр.keyboard.press('Enter'); стр.wait_for_timeout(300)
                о = стр.evaluate("() => (document.getElementById('lesson-3-2') || {}).style?.display")
                факт(о == 'block', f"{н} Enter на строке 3.2 открыл урок: {о}")
                # язык на открытом разделе
                стр.evaluate("() => { openSection('b3'); setLang('en'); }"); стр.wait_for_timeout(300)
                д2 = стр.evaluate(ВИД)
                факт(д2['тег'].strip().lower() == 'block 03' and д2['счёт'] == '5 of 11' and [х.lower() for х in д2['шапка']] == ['no.', 'lesson', 'about', 'status']
                     and д2['состояния'][4] == 'Next' and д2['состояния'][0] == 'Done' and д2['итог'].startswith('Completed'),
                     f"{н} английский без перерисовки: {д2['тег']!r}, {д2['счёт']!r}, {д2['шапка']}, {д2['состояния'][:1] + д2['состояния'][4:6]}, {д2['итог']!r}")
                стр.evaluate("() => setLang('ru')")
            стр.close()
    # крайние случаи
    for пройдено, имя in ((['3.' + str(и) for и in range(1, 12)], 'все пройдены'), ([], 'ни одного')):
        стр = открыть(бр, 1440, 900, 'light', пройдено)
        д = стр.evaluate(ВИД)
        if пройдено:
            факт(д['следСтрока'] == -1 and д['залито'] == 11 and д['следКлетка'] == -1 and д['счёт'] == '11 из 11', f"[{имя}] «Дальше» нет, полоса залита: {д['следСтрока']}, {д['залито']}, {д['счёт']!r}")
        else:
            факт(д['следСтрока'] == 0 and д['залито'] == 0 and д['следКлетка'] == 0 and д['счёт'] == '0 из 11', f"[{имя}] следующий — первый урок: {д['следСтрока']}, {д['следКлетка']}, {д['счёт']!r}")
        стр.close()
    бр.close()
с.shutdown()
важные = [о for о in ошибки if 'favicon' not in о]
факт(not важные, f"ошибок страницы нет: {важные[:2]}")
print("\n".join(отч))
if зам:
    print("НАХОДКИ:"); [print("  ✗", з) for з in зам]; sys.exit(1)
print("Чисто: раздел — таблицей с полосой уроков сверху, на 1440/1000/768/390 днём и ночью; нажатие, Enter и язык работают.")
