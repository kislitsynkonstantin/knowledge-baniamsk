# -*- coding: utf-8 -*-
"""Новые уроки помечены плашкой «New» — три месяца после добавления.

Константин 16.10.2026 попросил отметить шесть новых уроков точкой в меню, а
19.10.2026, снимком того же меню: «В базе к новым 6-ти статьям (где точки
ставили) поставь плашку New — пусть она висит 3 месяца».

Свежий урок — добавлен в базу не раньше 01.10.2026 (первый набор стоит с
added_at 01.09 — днём заполнения колонки) и меньше 92 дней назад. Пока его не
открывали, плашка залита жёлтым; открытый — та же плашка приглушённо.

Держит, на заглушке базы, на 1280 и 390 (на телефоне — в выдвинутом меню):
  • у свежих неоткрытых 2.1 и 3.12 плашка «New» залита, у свежего открытого
    3.13 — приглушена, у урока первого набора 3.1 плашки нет;
  • плашка в колонке галочек и стрелок блоков, не заходит на название и не
    обрезана краем меню;
  • в списке уроков раздела та же плашка после названия, тем же видом;
  • открытие урока приглушает его плашку и записывает прогресс в базу
    (status = in_progress), пройденным урок не считается;
  • через 92 дня после добавления плашки нет.

Запуск: python3 scratchpad/probes/check_kb_new_badge.py (из корня репозитория).
"""
import json, os, pathlib, threading, http.server, socketserver, functools, sys
from playwright.sync_api import sync_playwright

КОРЕНЬ = pathlib.Path(os.environ.get('BM_ROOT') or '/home/user/knowledge-baniamsk')
зам, отч = [], []
def факт(у, т): (отч if у else зам).append(("    ок  " if у else "") + т)


def тело(ид, н, заголовок, раздел):
    к = н.replace('.', '-')
    return (f'<div id="{ид}" style="display:none;"><div class="tag"><span class="lang-ru">Урок {н}</span><span class="lang-en">Lesson {н}</span></div>'
            f'<h2><span class="lang-ru">{заголовок}</span><span class="lang-en">Title {н}</span></h2>'
            f'<h3><span class="num">1.</span><span class="lang-ru">{раздел}</span><span class="lang-en">Section</span></h3>'
            f'<p><span class="lang-ru">Текст урока {н}.</span><span class="lang-en">Lesson text {н}.</span></p>'
            f'<div class="mark-complete" id="completeBox-{к}"><div class="mc-text"><h4><span class="lang-ru">Отметить урок как пройденный</span><span class="lang-en">Mark</span></h4></div>'
            f'<button class="mc-btn" id="completeBtn-{к}" onclick="toggleComplete(\'{н}\')"><span class="lang-ru">Отметить</span><span class="lang-en">Mark complete</span></button></div></div>')


НЕДАВНО = '2026-10-16T09:00:00Z'
УРОКИ = [
    dict(id='lesson-2-1', block=2, ord=1, status='ready', title_ru='Урок без места 2.1', title_en='Slotless 2.1',
         nav_ru='Предварительная концепция банного дома', nav_en='Nav 2.1', sub_ru='', sub_en='', added_at=НЕДАВНО, body_html=тело('lesson-2-1', '2.1', 'Урок без места 2.1', 'Раздел два-один')),
    dict(id='lesson-3-1', block=3, ord=1, status='ready', title_ru='Полное имя 3.1', title_en='Full 3.1',
         nav_ru='Меню 3.1', nav_en='Nav 3.1', sub_ru='', sub_en='', added_at='2026-09-01T00:00:00Z', body_html=тело('lesson-3-1', '3.1', 'Урок с местом 3.1', 'Раздел три-один')),
    dict(id='lesson-3-13', block=3, ord=13, status='ready', title_ru='Открытый новый 3.13', title_en='Opened new 3.13',
         nav_ru='После звонка о стоимости', nav_en='Nav 3.13', sub_ru='', sub_en='', added_at=НЕДАВНО, body_html=тело('lesson-3-13', '3.13', 'Открытый новый 3.13', 'Раздел')),
    dict(id='lesson-3-12', block=3, ord=12, status='ready', title_ru='Урок без места 3.12', title_en='Slotless 3.12',
         nav_ru='Решение премиального заказчика', nav_en='Nav 3.12', sub_ru='', sub_en='', added_at=НЕДАВНО, body_html=тело('lesson-3-12', '3.12', 'Урок без места 3.12', 'Сценарий встречи в шоуруме')),
]
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
    const данные = имя === 'kb_lesson_progress' ? [{ user_id: 'u1', lesson_id: '3.13', status: 'in_progress' }]
                 : имя === 'kb_lessons' ? window.__уроки
                 : имя === 'kb_blocks'  ? window.__блоки
                 : имя === 'profiles'   ? [{ id:'u1', email:'m@baniamsk.ru', full_name:'Проба', role:'manager' }]
                 : [];
    const ответ = { data: данные, error: null };
    const цепь = {
      select: () => цепь, order: () => цепь, eq: () => цепь, is: () => цепь,
      maybeSingle: async () => ({ data: данные[0] || null, error: null }),
      single: async () => ({ data: данные[0] || null, error: null }),
      then: (ф, о) => Promise.resolve(ответ).then(ф, о)
    };
    return { select: () => цепь, upsert: async (з) => { (window.__записи = window.__записи || []).push([имя, з]); return { error: null }; },
             update: () => цепь, insert: async () => ({ error: null }) };
  }
}) };
""" % (json.dumps(УРОКИ, ensure_ascii=False), json.dumps(БЛОКИ, ensure_ascii=False))

класс = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(КОРЕНЬ))
socketserver.TCPServer.allow_reuse_address = True
с = socketserver.TCPServer(("127.0.0.1", 0), класс)
threading.Thread(target=с.serve_forever, daemon=True).start()
порт = с.server_address[1]
ошибки = []
ПЛАШКИ = """() => { const р = {}; ['21', '31', '312', '313'].forEach(к => { const т = document.getElementById('newL' + к), п = document.getElementById('navL' + к);
  const вид = !!т && т.style.display !== 'none' && т.getClientRects().length > 0;
  const р_ = { вид, залита: вид && getComputedStyle(т).backgroundColor === 'rgb(250, 204, 21)', текст: т ? т.textContent.trim() : '' };
  if (вид && п) { const тр = т.getBoundingClientRect(); const имя = [...п.querySelectorAll('.lang-ru')].find(с => с.getClientRects().length);
    const ир = имя.getClientRects(); р_.зазор = Math.round(тр.left - Math.max(...[...ир].filter(x => x.bottom > тр.top && x.top < тр.bottom).map(x => x.right), -1e9));
    const ш = document.querySelector('.sb-group-chevron').getBoundingClientRect(); р_.кол = Math.round(Math.abs(тр.right - ш.right));
    const меню = document.querySelector('.sb').getBoundingClientRect(); р_.вМеню = тр.right <= меню.right && тр.left >= меню.left; }
  р[к] = р_; }); return р; }"""
ТАБЛИЦА = """() => { const р = {}; document.querySelectorAll('#secLessonList tbody tr').forEach(с => { const н = с.querySelector('.c-n').textContent.trim();
  const т = с.querySelector('.nw-tag'); р[н] = т ? (getComputedStyle(т).backgroundColor === 'rgb(250, 204, 21)' ? 'залита' : 'приглушена') : null; }); return р; }"""


def прогон(бр, ш):
    н = f"[{ш}]"
    стр = бр.new_page(viewport={"width": ш, "height": 900})
    стр.add_init_script(ЗАГЛУШКА)
    стр.on("pageerror", lambda e: ошибки.append(str(e)))
    стр.goto(f"http://127.0.0.1:{порт}/", wait_until="load")
    стр.wait_for_timeout(2500)
    if ш < 900:
        стр.evaluate("() => toggleMobMenu()"); стр.wait_for_timeout(400)
    т = стр.evaluate(ПЛАШКИ)
    факт(т['21']['залита'] and т['312']['залита'] and т['21']['текст'] == 'New', f"{н} у свежих неоткрытых 2.1 и 3.12 плашка «New» залита: {т['21']}, {т['312']}")
    факт(т['313']['вид'] and not т['313']['залита'], f"{н} у свежего открытого 3.13 плашка приглушена: {т['313']}")
    факт(not т['31']['вид'], f"{н} у урока первого набора 3.1 плашки нет: {т['31']}")
    факт(all(т[к].get('кол', 99) <= 3 for к in ('21', '312', '313')), f"{н} плашка в колонке стрелок блоков: смещение {[т[к].get('кол') for к in ('21', '312', '313')]} px")
    факт(all(т[к].get('зазор', 0) >= 4 for к in ('21', '312', '313')), f"{н} плашка не заходит на название: зазор {[т[к].get('зазор') for к in ('21', '312', '313')]} px")
    факт(all(т[к].get('вМеню') for к in ('21', '312', '313')), f"{н} плашка не обрезана краем меню")
    стр.screenshot(path=str(СНИМКИ / f"kb-new-menu-{ш}.png"))
    if ш < 900:
        стр.evaluate("() => toggleMobMenu()"); стр.wait_for_timeout(300)
    стр.evaluate("() => openSection('b3')"); стр.wait_for_timeout(500)
    тб = стр.evaluate(ТАБЛИЦА)
    факт(тб.get('3.12') == 'залита' and тб.get('3.13') == 'приглушена' and тб.get('3.1') is None,
         f"{н} в списке уроков раздела плашки как в меню: {тб}")
    стр.screenshot(path=str(СНИМКИ / f"kb-new-section-{ш}.png"))
    стр.evaluate("() => goLesson('3.12')"); стр.wait_for_timeout(400)
    т = стр.evaluate(ПЛАШКИ)
    записи = стр.evaluate("() => (window.__записи || []).filter(з => з[0] === 'kb_lesson_progress').map(з => з[1])")
    факт(т['312']['вид'] and not т['312']['залита'] and т['21']['залита'], f"{н} открытие 3.12 приглушает его плашку, у 2.1 залита: {т['312']}, {т['21']}")
    факт(any(з.get('lesson_id') == '3.12' and з.get('status') == 'in_progress' for з in записи), f"{н} открытие записано в прогресс: {записи}")
    стр.evaluate("() => showHomeScreen()"); стр.wait_for_timeout(300)
    метка = стр.evaluate("() => (document.getElementById('hsProgLabel') || {}).innerText || ''")
    факт(метка.strip().startswith('0'), f"{н} открытый урок не считается пройденным: «{метка.strip()}»")
    стр.evaluate("() => { const б = Date.now; Date.now = () => б() + 92 * 24 * 3600 * 1000; обновитьТочкиНовых(); }")
    т = стр.evaluate(ПЛАШКИ)
    факт(not any(т[к]['вид'] for к in т), f"{н} через 92 дня плашек нет: {[к for к in т if т[к]['вид']]}")
    стр.close()


СНИМКИ = pathlib.Path(os.environ.get('BM_SHOTS') or '/tmp')
with sync_playwright() as pw:
    бр = pw.chromium.launch(executable_path=os.environ.get('BM_CHROMIUM'), args=["--no-sandbox"])
    for ш in (1280, 390):
        прогон(бр, ш)
    бр.close()
с.shutdown()

важные = [о for о in ошибки if 'favicon' not in о]
факт(not важные, f"ошибок страницы нет: {важные[:2]}")
print("\n".join(отч)); print()
print("\n".join("ЗАМЕЧАНИЕ: " + з for з in зам) if зам else "Замечаний нет")
sys.exit(1 if зам else 0)
