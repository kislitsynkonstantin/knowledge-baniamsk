# -*- coding: utf-8 -*-
"""Проба логотипа в боковом меню базы знаний.

Константин 13.10.2026, снимком верха меню: «Тут поставь значок Баня МСК под
цвет темы и день/ночь с основного калькулятора».

Держит:
  • вместо плашки «БМСК» — логотип «Баня МСК» высотой 22 px, как в шапке
    калькулятора, номер версии рядом; картинка загружена, подпись есть;
  • логотип пиксель в пиксель совпадает с тем, что калькулятор рисует в
    своей шапке ночью (светлый логотип), — для каждого тона палитры: проба
    открывает калькулятор, берёт его перекрашенный логотип и параметры тона,
    передаёт те же параметры базе, как это делает сообщение tone, и сравнивает
    картинки по пикселям; по своей ссылке база сама встаёт в «Зелёный-графит»
    и логотип у неё такой же, как у калькулятора в этом тоне;
  • меню тёмное и днём, и ночью — поэтому логотип светлый в обоих случаях:
    белые буквы на меню читаются (контраст не ниже 4,5 : 1);
  • логотип не наезжает на номер версии и на кнопку меню, стоит в меню и
    на телефоне — в выдвижной панели.

Запуск: python3 scratchpad/probes/check_kb_sidebar_logo.py (из корня репозитория).
"""
import json, os, pathlib, threading, http.server, socketserver, functools, sys
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get('BM_KB') or '/home/user/knowledge-baniamsk')
КАЛЬК = pathlib.Path(os.environ.get('BM_ROOT') or '/home/user/-calculator-test')
ЗДЕСЬ = pathlib.Path(__file__).parent
ПРОБЫ_К = КАЛЬК / 'scratchpad' / 'probes'
зам, отч = [], []
def факт(у, т): (отч if у else зам).append(("    ок  " if у else "") + т)

ТОНЫ = ['', 'bmsk', 'sky', 'blue', 'amber', 'plum', 'indigo', 'graphite', 'titan']

ЗАГЛУШКА_КБ = """
const _сессия = { user: { id: 'u1', email: 'm@baniamsk.ru' }, access_token: 't' };
window.supabase = { createClient: () => ({
  auth: { getSession: async () => ({ data: { session: _сессия } }), onAuthStateChange: () => ({ data: { subscription: { unsubscribe(){} } } }),
          signInWithPassword: async () => ({ data: { session: _сессия }, error: null }), setSession: async () => ({ data: { session: _сессия }, error: null }), signOut: async () => ({}) },
  from: (имя) => {
    const данные = имя === 'kb_lessons' ? [{ id:'lesson-3-1', block:3, ord:1, status:'ready', title_ru:'Урок', title_en:'Lesson', nav_ru:'Урок', nav_en:'Lesson', sub_ru:'', sub_en:'', body_html:'<div id="lesson-3-1"><h2>Урок</h2></div>' }]
                 : имя === 'kb_blocks' ? [{ id:'b3', num:3, ord:3, name_ru:'Продажи', name_en:'Sales', sub_ru:'', sub_en:'' }]
                 : имя === 'profiles' ? [{ id:'u1', email:'m@baniamsk.ru', full_name:'Проба', role:'manager' }] : [];
    const ответ = { data: данные, error: null };
    const цепь = { select: () => цепь, order: () => цепь, eq: () => цепь, is: () => цепь, in: () => цепь,
      maybeSingle: async () => ({ data: данные[0] || null, error: null }), single: async () => ({ data: данные[0] || null, error: null }),
      then: (ф, о) => Promise.resolve(ответ).then(ф, о) };
    return { select: () => цепь, upsert: async () => ({ error: null }), update: () => цепь, insert: async () => ({ error: null }) };
  }
}) };
"""
# Отпечаток картинки: размер и два хеша по всем байтам пикселей.
ОТПЕЧАТОК = """async (src) => {
  const и = new Image(); await new Promise(r => { и.onload = r; и.onerror = r; и.src = src; });
  if (!и.naturalWidth) return null;
  const х = document.createElement('canvas'); х.width = и.naturalWidth; х.height = и.naturalHeight;
  const к = х.getContext('2d'); к.drawImage(и, 0, 0);
  const д = к.getImageData(0, 0, х.width, х.height).data; let h1 = 0, h2 = 0;
  for (let i = 0; i < д.length; i++) { h1 = (Math.imul(h1, 31) + д[i]) >>> 0; h2 = (h2 + д[i] * (i % 251 + 1)) >>> 0; }
  return [х.width, х.height, h1, h2];
}"""


class Тихий(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *а): pass


def сервер(корень):
    socketserver.TCPServer.allow_reuse_address = True
    с = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Тихий, directory=str(корень)))
    threading.Thread(target=с.serve_forever, daemon=True).start()
    return с, с.server_address[1]


с1, п1 = сервер(КОРЕНЬ)
с2, п2 = сервер(КАЛЬК)
хром = os.environ.get('BM_CHROMIUM') or str(sorted(pathlib.Path('/opt/pw-browsers').glob('chromium-*/chrome-linux/chrome'))[-1])
шрифты = (ПРОБЫ_К / 'шрифты_google.css').read_text(encoding='utf-8')
ошибки = []

with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=хром, args=["--no-sandbox"])

    # ── калькулятор: его логотип и параметры каждого тона ──
    к = бр.new_page(viewport={"width": 1280, "height": 800})
    к.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=шрифты))
    к.add_init_script((ПРОБЫ_К / 'stub_sb.js').read_text(encoding='utf-8'))
    к.goto(f"http://127.0.0.1:{п2}/index.html", wait_until="load"); к.wait_for_timeout(1500)
    эталон = {}
    for тон in ТОНЫ:
        э = к.evaluate("""async (тон) => {
          appSettings.tone = тон || 'teal';
          if (тон) await подготовитьКартинкиТона(тон);
          const п = параметрыТона(текущийТон());
          return { п, src: картинкаТона(_LOGO_LIGHT) };
        }""", тон)
        эталон[тон] = (э['п'], к.evaluate(ОТПЕЧАТОК, э['src']))
    к.close()
    факт(all(в[1] for в in эталон.values()), f"калькулятор отдал логотип каждого тона: {[т or 'teal' for т, в in эталон.items() if not в[1]] or 'все'}")
    факт(len({tuple(в[1]) for в in эталон.values() if в[1]}) == len(ТОНЫ), "у каждого тона свой логотип (проба различает тона)")

    def открыть(ш, в, схема):
        стр = бр.new_page(viewport={"width": ш, "height": в}, color_scheme=схема, device_scale_factor=2 if ш == 1440 else 1)
        стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=шрифты))
        стр.route("**/fonts.gstatic.com/**", lambda r: r.abort())
        стр.add_init_script(ЗАГЛУШКА_КБ)
        стр.on("pageerror", lambda e: ошибки.append(str(e)))
        стр.goto(f"http://127.0.0.1:{п1}/", wait_until="load"); стр.wait_for_timeout(1800)
        return стр

    def логотип(стр):
        return стр.evaluate("""() => { const л = document.getElementById('sbLogo'); return л ? л.src : null; }""")

    def дождаться(стр, ждём):
        """Холст перекрашивает логотип не сразу: опрашиваем, пока картинка не совпадёт или не выйдет время."""
        отп = None
        for _ in range(30):
            src = логотип(стр)
            отп = стр.evaluate(ОТПЕЧАТОК, src) if src else None
            if отп == ждём:
                break
            стр.wait_for_timeout(150)
        return отп

    # ── своя ссылка: «Зелёный-графит» сам ──
    стр = открыть(1440, 900, 'light')
    отп = дождаться(стр, эталон['bmsk'][1])
    факт(отп == эталон['bmsk'][1], f"по своей ссылке логотип — как у калькулятора в «Зелёном-графите»: {отп} / {эталон['bmsk'][1]}")
    # ── каждый тон — как сообщение tone ──
    несовпали = []
    for тон in ТОНЫ:
        п, отп_к = эталон[тон]
        стр.evaluate("(п) => перекраситьПоТону(document, п.сдвиг, п.насыщ, п.нейтр, п.свет)", п)
        отп = дождаться(стр, отп_к)
        if отп != отп_к:
            несовпали.append((тон or 'teal', отп, отп_к))
    факт(not несовпали, f"логотип пиксель в пиксель как у калькулятора во всех {len(ТОНЫ)} тонах: {несовпали or 'совпали'}")
    стр.close()

    # ── скрипт оборвался раньше (нет связи с базой): перекраска не падает ──
    # Так открывает базу проба тона калькулятора: без заглушки базы скрипт
    # обрывается на первом обращении к ней, и объявления ниже обрыва не
    # выполняются. Логотип с let в этом случае бросал «before initialization».
    стр = бр.new_page(viewport={"width": 1280, "height": 800})
    стр.route("**/fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=шрифты))
    стр.route("**/cdn.jsdelivr.net/**", lambda r: r.abort())
    свои = []
    стр.on("pageerror", lambda e: свои.append(str(e)))
    стр.goto(f"http://127.0.0.1:{п1}/", wait_until="load"); стр.wait_for_timeout(1200)
    до = list(свои)
    стр.evaluate("(п) => перекраситьПоТону(document, п.сдвиг, п.насыщ, п.нейтр, п.свет)", эталон['amber'][0])
    отп = дождаться(стр, эталон['amber'][1])
    после = [о for о in свои[len(до):]]
    факт(not после and отп == эталон['amber'][1], f"без связи с базой перекраска не падает и логотип перекрашен: ошибки {после[:1]}, совпал {отп == эталон['amber'][1]}")
    стр.close()

    # ── вид: днём и ночью, компьютер и телефон ──
    for ш, в in ((1440, 900), (390, 844)):
        for схема in ('light', 'dark'):
            н = f"[{ш} {'день' if схема == 'light' else 'ночь'}]"
            стр = открыть(ш, в, схема)
            if ш <= 880:
                стр.evaluate("() => { document.getElementById('sidebar').classList.add('mob-open'); const б = document.getElementById('mobBackdrop'); if (б) б.classList.add('on'); }")
                стр.wait_for_timeout(500)
            д = стр.evaluate("""() => {
              const л = document.getElementById('sbLogo'), меню = document.getElementById('sidebar');
              if (!л) return { нет: true, плашка: !!document.querySelector('.sb-logo-badge') };
              const б = л.getBoundingClientRect(), м = меню.getBoundingClientRect();
              const рядом = [...меню.querySelectorAll('.sb-ver, button, .sb-floating, [class*="pin"]')].filter(э => э !== л && э.getClientRects().length && getComputedStyle(э).visibility !== 'hidden');
              const зазор = Math.min(...рядом.map(э => { const р = э.getBoundingClientRect();
                const dx = Math.max(р.left - б.right, б.left - р.right, 0), dy = Math.max(р.top - б.bottom, б.top - р.bottom, 0); return Math.round(Math.hypot(dx, dy)); }));
              const rgb = s => (/rgba?\\(([^)]+)\\)/.exec(s) || [0, '255,255,255'])[1].split(',').map(Number);
              const я = ([r, g, b]) => { const к = v => (v /= 255) <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; return .2126 * к(r) + .7152 * к(g) + .0722 * к(b); };
              const фон = я(rgb(getComputedStyle(меню).backgroundColor));
              return { нет: false, высота: Math.round(б.height), загружен: л.complete && л.naturalWidth > 0, подпись: л.alt,
                       внутри: б.left >= м.left && б.right <= м.right && б.top >= м.top, зазор,
                       контраст: Math.round((1.05 / (фон + .05)) * 10) / 10, видно: б.width > 0 && getComputedStyle(л).visibility !== 'hidden',
                       плашка: !!document.querySelector('.sb-logo-badge'), версия: (document.querySelector('.sb-ver') || {}).textContent || '' };
            }""")
            if д['нет']:
                факт(False, f"{н} логотипа в меню нет (плашка «БМСК» на месте: {д['плашка']})")
                стр.close(); continue
            факт(д['видно'] and д['загружен'] and д['высота'] == 22 and д['подпись'] == 'Баня МСК', f"{н} логотип виден, загружен, 22 px, подпись: {д['высота']}, {д['загружен']}, {д['подпись']!r}")
            факт(not д['плашка'] and д['версия'] == 'v2.19', f"{н} плашки «БМСК» нет, версия рядом: {д['плашка']}, {д['версия']!r}")
            факт(д['внутри'] and д['зазор'] >= 6, f"{н} логотип в меню, до соседей не меньше 6 px: {д['внутри']}, {д['зазор']} px")
            факт(д['контраст'] >= 4.5, f"{н} меню тёмное — белые буквы логотипа читаются: {д['контраст']} : 1")
            стр.screenshot(path=str(ЗДЕСЬ / f"логотип-меню-{ш}-{схема}.png"), clip={"x": 0, "y": 0, "width": 300 if ш > 880 else 300, "height": 200})
            стр.close()
    бр.close()
с1.shutdown(); с2.shutdown()
важные = [о for о in ошибки if 'favicon' not in о]
факт(not важные, f"ошибок страницы нет: {важные[:2]}")
print("\n".join(отч))
if зам:
    print("НАХОДКИ:"); [print("  ✗", з) for з in зам]; sys.exit(1)
print("Чисто: в меню базы — логотип калькулятора, пиксель в пиксель в каждом тоне; меню тёмное днём и ночью, светлый логотип читается.")
