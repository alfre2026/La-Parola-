#!/usr/bin/env python3
"""Ritocchi alla traduzione italiana (mh/it) confrontandola con l'originale (mh/en).

- Date dei titoli: «(b. c. 1491.)» -> «(1491 a.C.)», «(a. d. 58.)» -> «(58 d.C.)»
  (il traduttore automatico le rendeva in modi diversi, a volte sbagliati).
- Spazi prima della punteggiatura.

Uso: fix_it.py <mh/en> <mh/it>
"""
import json, os, re, sys, glob

DATE = re.compile(r'\s*\(\s*(b|a)\.\s*([cd])\.\s*(\d{1,4})\.?\s*\)\s*$', re.I)
TAIL = re.compile(r'\s*\([^()]*\d[^()]*\)\s*$')


# nomi propri rimasti in inglese -> forma italiana (Nuova Riveduta)
NAMES = dict(x.split(':') for x in '''David:Davide Haman:Aman Jehu:Ieu Jonathan:Gionatan Jezebel:Izebel Esther:Ester
Ruth:Rut Mordecai:Mardocheo Nazareth:Nazaret Jacob:Giacobbe Nathan:Natan Simon:Simone Hannah:Anna Gideon:Gedeone
Joshua:Giosuè Deborah:Debora Paul:Paolo Elias:Elia Obadiah:Abdia Sarah:Sara John:Giovanni Ezra:Esdra Aaron:Aaronne
Peter:Pietro Micah:Michea Daniel:Daniele Uriah:Uria Joseph:Giuseppe Samuel:Samuele Hagar:Agar Thomas:Tommaso
Zebulun:Zabulon Nahum:Naum Reuben:Ruben Rachel:Rachele Stephen:Stefano Benjamin:Beniamino Leah:Lea Asher:Ascer
Rahab:Raab Andrew:Andrea James:Giacomo Moses:Mosè Abraham:Abraamo Isaac:Isacco Solomon:Salomone Elijah:Elia
Elisha:Eliseo Noah:Noè Adam:Adamo Judas:Giuda Philip:Filippo Mary:Maria Martha:Marta Lazarus:Lazzaro Pilate:Pilato
Herod:Erode Pharaoh:Faraone Isaiah:Isaia Jeremiah:Geremia Ezekiel:Ezechiele Jonah:Giona Samson:Sansone
Hezekiah:Ezechia Josiah:Giosia Timothy:Timoteo Barnabas:Barnaba Silas:Sila Jerusalem:Gerusalemme Egypt:Egitto
Babylon:Babilonia Israel:Israele Galilee:Galilea Judah:Giuda Jordan:Giordano Zion:Sion Rebekah:Rebecca Esau:Esaù
Cain:Caino Abel:Abele Ishmael:Ismaele Ephraim:Efraim Manasseh:Manasse Simeon:Simeone Naphtali:Neftali
Issachar:Issacar Jephthah:Iefte Rehoboam:Roboamo Jeroboam:Geroboamo Jehoshaphat:Giosafat Nehemiah:Neemia
Hosea:Osea Habakkuk:Abacuc Zephaniah:Sofonia Haggai:Aggeo Zechariah:Zaccaria Malachi:Malachia Zacharias:Zaccaria
Elisabeth:Elisabetta Zaccheus:Zaccheo Caiaphas:Caiafa Matthias:Mattia Cornelius:Cornelio Onesimus:Onesimo
Bethlehem:Betlemme Corinth:Corinto Ephesus:Efeso Rome:Roma Greece:Grecia Crete:Creta Antioch:Antiochia
Damascus:Damasco Job:Giobbe Eve:Eva Matthew:Matteo Mark:Marco Luke:Luca'''.split())
NAMES_RE = re.compile(r'\b(' + '|'.join(sorted(NAMES, key=len, reverse=True)) + r")\b(?!\s+Henry)")


def names(t):
    return NAMES_RE.sub(lambda m: NAMES[m.group(1)], t)


def tidy(t):
    t = names(t)
    t = re.sub(r'\b(\w+)(?:\s+\1\b){2,}', r'\1', t)      # «divina divina divina…»: ripetizione del traduttore
    t = re.sub(r'\s+([,.;:!?)\]])', r'\1', t)
    t = re.sub(r'([(\[])\s+', r'\1', t)
    return re.sub(r'\s{2,}', ' ', t).strip()


def fix_title(en, it):
    m = DATE.search((en or '').replace('\xa0', ' '))
    if not m or not it:
        return it
    era = 'a.C.' if m.group(1).lower() == 'b' else 'd.C.'
    base = TAIL.sub('', it).rstrip()
    return f'{base} ({m.group(3)} {era})'


def main():
    en_dir, it_dir = sys.argv[1], sys.argv[2]
    n = 0
    for f in sorted(glob.glob(os.path.join(it_dir, '*.json'))):
        it = json.load(open(f, encoding='utf-8'))
        en = json.load(open(os.path.join(en_dir, os.path.basename(f)), encoding='utf-8'))
        by_r = {u['r']: u for u in en['u']}
        for u in it['u']:
            e = by_r.get(u['r'])
            if e and u.get('t') and u['k'] == 'p':
                t = fix_title(e.get('t'), names(u['t']))
                if t != u['t']:
                    u['t'] = t
                    n += 1
            ps = [tidy(p) for p in u['p']]
            if e and len(e['p']) == len(ps):   # traduzione troncata (elenchi di riferimenti): resta l'originale
                ps = [pe if len(pe) > 80 and len(pi) < 0.6 * len(pe) else pi for pe, pi in zip(e['p'], ps)]
            u['p'] = ps
        with open(f, 'w', encoding='utf-8') as fh:
            json.dump(it, fh, ensure_ascii=False, separators=(',', ':'))
    print('titoli corretti:', n)


if __name__ == '__main__':
    main()
