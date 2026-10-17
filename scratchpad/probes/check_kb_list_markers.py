# -*- coding: utf-8 -*-
"""Точки маркированных списков в уроках — тёмным цветом темы, а не чёрным.

Константин 17.10.2026, снимком списка из документа с цветными точками: «В базе
знаний и справке в документах, где обычные тут чёрные точки маркированного
списка, поставь тёмные в цвет темы».

Держит, на заглушке базы, днём и ночью, по своей ссылке («Зелёный-графит») и
внутри калькулятора (бирюза):
  • точка списка в уроке — цвета темы (оттенок --g), а не текста и не серая;
    у «Зелёного-графита» днём — темнее --g: тот средний зелёный на листе
    даёт 2,5 : 1;
  • точка видна на фоне урока: контраст не меньше 3 : 1, как у значков;
  • в плашке предупреждения точка — цвета её черты, а не бирюзы: плашка тёплая.

Проверено возвращением дефекта: на прежней версии страницы точка цвета текста —
проба краснеет.

Запуск: python3 scratchpad/probes/check_kb_list_markers.py (из корня репозитория).
"""
import colorsys, json, os, pathlib, threading, http.server, socketserver, functools, sys
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get('BM_ROOT') or '/home/user/knowledge-baniamsk')
зам, отч = [], []
def факт(у, т): (отч if у else зам).append(("    ок  " if у else "") + т)

ТЕЛО = ('<div id="lesson-3-1" style="display:none;"><div class="tag"><span class="lang-ru">Урок 3.1</span><span class="lang-en">Lesson 3.1</span></div>'
        '<h2><span class="lang-ru">Учебный урок</span><span class="lang-en">Sample</span></h2>'
        '<p><span class="lang-ru">Перед списком.</span><span class="lang-en">Before.</span></p>'
        '<ul id="пробаСписок"><li><span class="lang-ru">Первый пункт</span><span class="lang-en">First</span></li>'
        '<li><span class="lang-ru">Второй пункт</span><span class="lang-en">Second</span></li></ul>'
        '<div class="warn"><strong><span class="lang-ru">Внимание.</span><span class="lang-en">Note.</span></strong>'
        '<ul id="пробаПлашка"><li><span class="lang-ru">Пункт в плашке</span><span class="lang-en">Item</span></li></ul></div></div>')
УРОКИ = [dict(id='lesson-3-1', block=3, ord=1, status='ready', title_ru='Учебный урок 3.1', title_en='Sample 3.1',
              nav_ru='Меню 3.1', nav_en='Nav 3.1', sub_ru='', sub_en='', added_at='2026-09-01T00:00:00Z', body_html=ТЕЛО)]
БЛОКИ = [dict(id='b%d' % н, num=н, ord=н, name_ru='Блок %d' % н, name_en='Block %d' % н, sub_ru='', sub_en='') for н in (1, 2, 3, 4, 5)]

ЗАГЛУШКА = """
window.__уроки = %s; window.__блоки = %s;
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
                 : имя === 'kb_blocks' ? window.__блоки
                 : имя === 'profiles' ? [{ id:'u1', email:'m@baniamsk.ru', full_name:'Проба', role:'manager' }] : [];
    const ответ = { data: данные, error: null };
    const цепь = { select: () => цепь, order: () => цепь, eq: () => цепь, is: () => цепь,
      maybeSingle: async () => ({ data: данные[0] || null, error: null }),
      single: async () => ({ data: данные[0] || null, error: null }),
      then: (ф, о) => Promise.resolve(ответ).then(ф, о) };
    return { select: () => цепь, upsert: async () => ({ error: null }), update: () => цепь, insert: async () => ({ error: null }) };
  }
}) };
""" % (json.dumps(УРОКИ, ensure_ascii=False), json.dumps(БЛОКИ, ensure_ascii=False))

ТОЧКИ = """() => {
  // Цвет из color-mix() браузер отдаёт как color(srgb 0.3 0.47 0.14) — читаем и его.
  const к = s => { const м = /rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?/.exec(s || '');
    if (м) return { c: [+м[1], +м[2], +м[3]], a: м[4] == null ? 1 : +м[4] };
    const с = /color\\(srgb\\s+([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)(?:\\s*\\/\\s*([\\d.]+))?/.exec(s || '');
    return с ? { c: [с[1], с[2], с[3]].map(x => Math.round(+x * 255)), a: с[4] == null ? 1 : +с[4] } : null; };
  const цвет = (знач, где) => { const и = document.createElement('i'); и.style.color = знач; (где || document.body).appendChild(и); const ц = getComputedStyle(и).color; и.remove(); return к(ц).c; };
  const фон = э => { for (let у = э; у; у = у.parentElement) { const ц = к(getComputedStyle(у).backgroundColor); if (ц && ц.a > 0.5) return ц.c; }
    return к(getComputedStyle(document.documentElement).backgroundColor).c; };
  const пункт = document.querySelector('#пробаСписок li'), вПлашке = document.querySelector('#пробаПлашка li');
  if (!пункт || !пункт.getClientRects().length) return null;
  return { точка: к(getComputedStyle(пункт, '::marker').color).c, текст: к(getComputedStyle(пункт).color).c, тема: цвет('var(--g)', пункт),
           фон: фон(пункт), плашка: к(getComputedStyle(вПлашке, '::marker').color).c, черта: цвет('var(--warn-border)', вПлашке) };
}"""


def тон(rgb):
    h, l, s = colorsys.rgb_to_hls(*(x / 255 for x in rgb))
    return h * 360, s


def яркость(rgb):
    л = [((x / 255) / 12.92 if x / 255 <= 0.03928 else (((x / 255) + 0.055) / 1.055) ** 2.4) for x in rgb]
    return 0.2126 * л[0] + 0.7152 * л[1] + 0.0722 * л[2]


def контраст(а, б):
    я = sorted([яркость(а), яркость(б)], reverse=True)
    return (я[0] + 0.05) / (я[1] + 0.05)


класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
class Тихий(класс.func):
    def log_message(self, *а): pass
socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(КОРЕНЬ)))
threading.Thread(target=с.serve_forever, daemon=True).start()
порт = с.server_address[1]
ошибки = []
хром = os.environ.get('BM_CHROMIUM') or str(sorted(pathlib.Path('/opt/pw-browsers').glob('chromium-*/chrome-linux/chrome'))[-1])
with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])
    for где, адрес in (('своя ссылка', '/'), ('в калькуляторе', '/?embed=1')):
        for схема in ('light', 'dark'):
            стр = бр.new_page(viewport={"width": 1440, "height": 900}, color_scheme=схема)
            стр.add_init_script(ЗАГЛУШКА)
            стр.on("pageerror", lambda e: ошибки.append(str(e)))
            стр.goto(f"http://127.0.0.1:{порт}{адрес}", wait_until="load"); стр.wait_for_timeout(1800)
            стр.evaluate("() => goLesson('3.1')"); стр.wait_for_timeout(500)
            в = стр.evaluate(ТОЧКИ)
            м = f"[{где}, {схема}]"
            факт(в is not None, f"{м} урок со списком открыт")
            if not в:
                стр.close(); continue
            отч.append(f"    {м} {в}")
            (ht, st), (hm, sm) = тон(в['тема']), тон(в['точка'])
            факт(в['точка'] != в['текст'] and sm >= 0.25 and min(abs(ht - hm), 360 - abs(ht - hm)) <= 12,
                 f"{м} точка цвета темы {в['тема']} (оттенок {ht:.0f}°), а не текста {в['текст']}: {в['точка']} (оттенок {hm:.0f}°, насыщенность {sm:.2f})")
            факт(контраст(в['точка'], в['фон']) >= 3, f"{м} точка видна на фоне {в['фон']}: контраст {контраст(в['точка'], в['фон']):.2f}")
            факт(в['плашка'] == в['черта'], f"{м} в плашке предупреждения точка цвета черты {в['черта']}: {в['плашка']}")
            if not os.environ.get('BM_ROOT') and где == 'своя ссылка':
                стр.locator('#пробаСписок').screenshot(path=str(pathlib.Path(__file__).parent / f"точки-{схема}.png"))
            стр.close()
    бр.close()
с.shutdown()
факт(not ошибки, f"ошибок страницы нет: {ошибки[:3]}")
print("\n".join(отч))
if зам:
    print("НАХОДКИ:"); [print("  ✗", з) for з in зам]; sys.exit(1)
print("Чисто: точки списков в уроках — цвета темы днём и ночью, в «Зелёном-графите» и в калькуляторе; в плашке предупреждения — цвета её черты.")
