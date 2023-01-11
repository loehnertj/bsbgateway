# coding: utf8

##############################################################################
#
#    Part of BsbGateway
#    Copyright (C) Johannes Loehnert, 2013-2015
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import itertools as it
from .bsb_field import BsbField, BsbFieldChoice, BsbFieldInt8, BsbFieldInt16, BsbFieldInt32, BsbFieldTemperature, BsbFieldTime

__all__ = ['groups', 'fields', 'fields_by_telegram_id']

# Shorthands for recurring kwargs
RW = {'rw':True}
RWN = {'rw':True, 'nullable': True}
ONOFF_RW = {'rw': True, 'choices': {0: u'Aus', 255: u'Ein'}}
OP_HOURS = {'unit': 'h', 'tn': 'HOURS', 'divisor': 3600}

_choices_heizkreis = {
    0  : u'---',
    3  : u'Wächter angesprochen',
    4  : u'Handbetrieb aktiv',
    102: u'Estrichfunktion aktiv',
    56 : u'Überhitzschutz aktiv',
    103: u'Eingeschränkt, Kesselschutz',
    104: u'Eingeschränkt, TWW-Vorrang',
    105: u'Eingeschränkt, Puffer',
    106: u'Heizbetrieb eingeschränkt',
    107: u'Zwangsabnahme Puffer',
    108: u'Zwangsabnahme TWW',
    109: u'Zwangsabnahme Erzeuger',
    110: u'Zwangsabnahme',
    17 : u'Nachlauf aktiv',
    111: u'Einschaltopt + Schnellaufheiz',
    112: u'Einschaltoptimierung',
    113: u'Schnellaufheizung',
    114: u'Heizbetrieb Komfort',
    115: u'Ausschaltoptimierung',
    116: u'Heizbetrieb Reduziert',
    101: u'Raumfrostschutz aktiv',
    117: u'Vorlauffrostschutz aktiv',
    23 : u'Anlagenfrostschutz aktiv',
    24 : u'Frostschutz aktiv',
    118: u'Sommerbetrieb',
    119: u'Tages-Eco aktiv',
    120: u'Absenkung Reduziert',
    121: u'Absenkung Frostschutz',
    122: u'Raumtemp’begrenzung',
    25 : u'Aus',
}

class Group(object):
    def __init__(o, disp_id, name, fields):
        o.disp_id = disp_id
        o.name = name
        o.fields = fields

groups = [
    Group(700, "700 Heizkreis 1", [
        BsbFieldChoice(0x2d3d0574, 700, u'Betriebsartwahl HK - 1', choices={
            0: u'Schutzbetrieb',
            1: u'Automatik',
            2: u'Dauerhaft Reduziert heizen',
            3: u'Dauerhaft Komfort heizen',
        }, **RW),

        # 710 19°C ret 710 Komfortsollwert = [0, 4, 192] [raw:00 04 C0 ] @1670337788.529230> 14-35
        # 712 14°C ret 712 Reduziertsollwert = [0, 3, 128]  10-19
        # 714 10°C ret 714 Frostschutzsollwert = [0, 2, 128] 4-14
        # 720 0.78 720 Kennlinie Steilheit = [0, 0, 39] 0.1 - 4.0 / 0.5 = [0 0 25]
        # 721 1.5°C Kennlinie Verschiebung = [0, 0, 96] -4.5 - +4.5
        # 726 Aus Kennlinie Adaption = [0, 0] ; Ein = [0 255]; Set [1 0] bzw [1 255]
        BsbFieldTemperature(0x2d3d058e, 710, u'Komfortsollwert', min=14.0, max=35.0, **RW),
        BsbFieldTemperature(0x2d3d0590, 712, u'Reduziertsollwert', min=10.0, max=19.0, **RW),
        BsbFieldTemperature(0x2d3d0592, 714, u'Frostschutzsollwert', min=4.0, max=14.0, **RW),
        BsbFieldInt16(0x2d3d05f6, 720, u'Kennlinie Steilheit', min=0.1, max=4.0, divisor=50.0, tn="FP02", **RW),
        BsbFieldTemperature(0x2d3d0610, 721, u'Kennlinie Verschiebung', min=-4.5, max=4.5, **RW),
        BsbFieldChoice(0x2d3d060b, 726, u'Kennlinie Adaption', **ONOFF_RW),

        #730 19°C Sommer-/Winterheizgrenze = [0, 4, 192]  ---, 8-30
        # 732 0°C Tagesheizgrenze = [0, 0, 0] --, -10-10
        # 740 12°C Vorlaufsollwert Minimum = [0, 3, 0] 8-95
        # 741 54°C Vorlaufsollwert Maximum = [0, 13, 128] 8-95
        # 742 --°C Vorlaufsollw Raumthermostat 0x213D0A88 = [1, 16, 64] set mit 5/6 --, 8-95
        # 750 --% Raumeinfluss = [1, 1]  2% = [0, 2] 100% = [0, 100] set mit 5/6 --, 0-100%
        BsbFieldTemperature(0x2d3d05fd, 730, u'Sommer-/Winterheizgrenze', min=8.0, max=30.0, **RWN ),
        BsbFieldTemperature(0x2d3d0640, 732, u'Tagesheizgrenze', min=-10, max=10, **RWN),
        BsbFieldTemperature(0x213d0663, 740, u'Vorlaufsollwert Minimum', min=8, max=95, **RW),
        BsbFieldTemperature(0x213d0662, 741, u'Vorlaufsollwert Maximum', min=8, max=95, **RW),
        BsbFieldTemperature(0x213d0a88, 742, u'Vorlaufsollwert Raumthermostat', min=8.0, max=95.0, **RWN),
        BsbFieldInt8(0x2d3d0603, 750, u'Raumeinfluss', min=0, max=100, unit=u"%", tn="PERCENT", **RWN),

        # 760 --°C Raumtemperaturbegrenzung = [1, 0, 32] nullable --, 0.5...4°C
        # 770 --°C Schnellaufheizung = [1, 0, 0] nullable --, 0-20
        # 780 ENUM Schnellabsenkung
        #   0 = Aus
        #   1 = Bis Reduziertsollwert
        #   2 = Bis Frostschutzsollwert
        # 790 0 min Einschalt-Optimierung Max = [0, 0, 0, 0, 0]  10 min = [..0 2 88] 20 min = [... 0 4 176]  120 min = [... 28 32] not null --- 0-360 min
        # 791 0 min Ausschalt-Optimierung Max = [0, 0, 0, 0, 0] 360 min = .... 84, 96] notnull 0-360 min
        BsbFieldTemperature(0x2d3d0614, 760, u'Raumtemperaturbegrenzung', min=0.5, max=4.0, **RWN),
        BsbFieldTemperature(0x2d3d0602, 770, u'Schnellaufheizung', min=0, max=20, **RWN),
        BsbFieldChoice(0x2d3d05e8, 780, u'Schnellabsenkung', choices={
            0: u"Aus", 1: u"Bis Reduziertsollwert", 2: u"Bis Frostschutzsollwert"
        }, **RW),
        BsbFieldInt32(0x2d3d0607, 790, u'Einschalt-Optimierung Max', min=0, max=360, divisor=60, unit=u"min", tn="MINUTES", **RW),
        BsbFieldInt32(0x2d3d0609, 791, u'Ausschalt-Optimierung Max', min=0, max=360, divisor=60, unit=u"min", tn="MINUTES", **RW),

        # 800 --°C Reduziert-Anhebung Beginn = [1, 254, 192]  -15°C = [0 252 64] null --, -15 - 10
        # 801 -15°C Reduziert-Anhebung Ende NN -30 - -15
        # 809 HK1 Pumpendauerlauf Enum  0x053D1289 
        #   0 = Nein
        #   255 = Ja - NN
        # 820 ÜBerhitzschutz Pumpenkreis ENum 0x213D0674 
        #   0 = Aus
        #   255 = Ein
        # 830 5°C HK1 Mischerüberhöhung 0x213D065D 0-50°C
        # 834 120s HK1 ANtrieb Laufzeit 0x213D065A = [0, 0, 120] 30-873s 30 = 0 0 30 /  873 = 00 3 105
        # XX 850  Estrich-Funktion 0=Aus, 855 = Estrich Sollwert aktuell
        BsbFieldTemperature(0x2d3d059e, 800, u'Reduziert-Anhebung Beginn', min=-15, max=10, **RWN),
        BsbFieldTemperature(0x2d3d059d, 801, u'Reduziert-Anhebung Ende', min=-30, max=-15, **RWN),
        BsbFieldChoice(0x053D1289, 809, u"Pumpendauerlauf", **ONOFF_RW),
        BsbFieldChoice(0x213D0674, 820, u"Überhitzschutz Pumpenkreis", **ONOFF_RW),
        BsbFieldTemperature(0x213D065D, 830, u"Mischerüberhöhung", min=0, max=50, **RW),
        BsbFieldInt16(0x213D065A, 834, u"Antrieb Laufzeit", min=0, max=120, unit=u"s", tn="SECONDS_WORD", **RW),
        # Absichtlich ausgeblendet!!
        #BsbField(0x2d3d067b, 850, u'Estrich-Funktion ', ),
        #BsbField(0x2d3d068a, 851, u'Estrich Sollwert manuell', ),

        # 861 Übertemperaturabnahme Enum 0x213D08C9 = [0, 1]
        #   0=Aus
        #   1=Heizbetrieb
        #   2=Immer
        # 870 Mit Pufferspeicher 0x2D3D07C4 = [0, 0]
        #   0=Nein, 255=Ja
        # 872 Mit VOrregler / Zubringpumpe 0x2D3D07C5 = [0, 0] 0=nein 255=ja
        # 880 HK1 PUmpe Drehzahlreduktion 0x213D04AD 
        #   0 = Betriebsniveau
        #   1 = Kennlinie
        # 882 30% Pumpendrehzahl Minimum 0x053D115E = [0, 30] 0-100%
        # 883 100% Pumpendrehzahl MAximum 0x053D115F = [0, 100] 0-100%
        BsbFieldChoice(0x213D08C9, 861, u"Übertemperaturabnahme", choices={
            0: u"Aus", 1: u"Heizbetrieb", 2: u"Immer",
        }, **RW),
        BsbFieldChoice(0x2D3D07C4, 870, u"Mit Pufferspeicher", **ONOFF_RW),
        BsbFieldChoice(0x2D3D07C5, 872, u"Mit Vorregler / Zubringpumpe", **ONOFF_RW),
        BsbFieldChoice(0x213D04AD, 880, u"Pumpe Drehzahlreduktion", choices={
            0: u"Betriebsniveau", 1: u"Kennlinie",
        }, **RW),
        BsbFieldInt8(0x053D115E, 882, u"Pumpendrehzahl Minimum", min=0, max=100, unit=u"%", tn="PERCENT", **RW),
        BsbFieldInt8(0x053D115F, 883, u"Pumpendrehzahl Maximum", min=0, max=100, unit=u"%", tn="PERCENT", **RW),

        # 888 10% Kennliniekorr. bei 50% Drehz 0x213D0E38 = [0, 10] 0-100%
        # 890 Vorlaufsollwertkorrektur Drehzahlregelung 0x213D10C2 = [0, 255] 0=nein, 255=ja
        # 898 Betriebsniveauumschaltung 0x053D0DD4 = [0, 1]
        #   0= Frostschutz
        #   1 = Reduziert
        #   2 = Komfort
        # 900 Betriebsartumschaltung 0x053D0DD4 = [0, 1] !??
        #   0 = Keine
        #   1 = Schutzbetrieb
        #   2 = Reduziert
        #   3 = Komfort
        #   4 = Automatik
        BsbFieldInt8(0x213D0E38, 888, u"Kennnlinienkorrektur bei 50% Drehzahl", min=0, max=100, unit=u"%", tn="PERCENT", **RW),
        BsbFieldChoice(0x213D10C2, 890, u"Vorlaufsollwertkorrektur Drehzahlregelung", **ONOFF_RW),
        BsbFieldChoice(0x053D0DD4, 898, u"Betriebsniveauumschaltung", choices={
            0: u"Frostschutz", 1: u"Reduziert", 2: u"Komfort",
        }, **RW),
        BsbFieldChoice(0x053D07BE, 10900, u"Betriebsartumschaltung", choices={
            0: u"Keine",
            1: u"Schutzbetrieb",
            2: u"Reduziert",
            3: u"Komfort",
            4: u"Automatik",
        }, **RW)
    ]),
    Group(1600, "1600 Trinkwasser", [
        BsbFieldChoice(0x313d0571, 10111, u'Trinkwasserbereitung', choices=["Aus", "Ein"], **RW),
        # Menü Trinkwasser
        BsbFieldTemperature(0x313d06b9, 1610, u'Nennsollwert', min=23, max=65, **RW),
        BsbFieldTemperature(0x313d06ba, 1612, u'Reduziertsollwert', min=8, max=40, **RW),
        BsbFieldChoice(0x253d0722, 1620, u'Freigabe', choices=[
            '24h/Tag',
            'Zeitprogramm Heizkreise',
            'Zeitprogramm 4/TWW'
        ], **RW),
        BsbFieldChoice(0x313d0759, 1640, u'Legionellenfunktion', choices=[
            'Aus',
            'Periodisch',
            'Fixer Wochentag',
        ], **RW),
        BsbFieldInt8(0x313d0738, 1641, u'Legionellenfkt Periodisch', min=1, max=7, tn="DAYS", **RW),
        BsbFieldChoice(0x313d075e, 1642, u'Legionellenfkt Wochentag', choices=[
            '',
            'Montag',
            'Dienstag',
            'Mittwoch',
            'Donnerstag',
            'Freitag',
            'Samstag',
            'Sonntag',
        ], **RW),
        BsbFieldTime(0x313d075a, 1644, u'Legionellenfunktion Zeitpunkt', **RWN),
        BsbFieldTemperature(0x313d06bc, 1645, u'Legionellenfunktion Sollwert', min=55, max=95, **RW),
        BsbFieldInt16(0x313d0496, 1646, u'Legionellenfunktion Verweildauer', min=10, max=360, tn="MINUTES_WORD", **RWN),
        BsbFieldChoice(0x313d08ab, 1647, u'Legionellenfkt Zirk’pumpe', choices=['Aus', 'Ein'], **RW),
        BsbFieldChoice(0x253d072e, 1660, u'Zirkulationspumpe Freigabe', choices=[
            '',
            'Zeitprogramm 3/HKP',
            'Trinkwasser Freigabe',
            'Zeitprogramm 4/TWW',
            'Zeitprogramm 5',
        ], **RW),
        BsbFieldChoice(0x253d0689, 1661, u'Zirk’pumpe Taktbetrieb', choices=['Aus', 'Ein'], **RW),
        BsbFieldTemperature(0x253D077E, 1663, u'Trinkwasser Zirkulationssollwert', min=8, max=40, **RW),
        BsbFieldChoice(0x053D0E84, 1680, u'Trinkwasser Betriebsartumschaltung', choices=['Keine', 'Aus', 'Ein'], **RW),
    ]),
        
    Group(2000, "2000 Kessel", [
        BsbFieldChoice(0x0D3D0949, 2200, u'Betriebsart', choices={
            0: u'Dauerbetrieb',
            2: u'Auto, verlängerte Laufzeit',
        }),
        BsbFieldChoice(0x0D3D08D3, 2201, u'Erzeugersperre', choices=['Aus', 'Ein']),
        BsbFieldTemperature(0x113D04D3, 2203, u'Freigabe unter Außentemperatur', ),
        BsbFieldTemperature(0x113D11F3, 2204, u'Freigabe über Außentemperatur', ),
        BsbFieldChoice(0x05050D20, 7119, u'Ökofunktion', choices=['Aus', 'Ein']),
        BsbFieldChoice(0x053D0D20, 10119, u'Ökofunktion', choices=['Aus', 'Ein']),
        BsbFieldChoice(0x05050B4E, 7120, u'Ökobetrieb', choices=['Aus', 'Ein']),
        BsbFieldChoice(0x053D0B4E, 10120, u'Ökobetrieb', choices=['Aus', 'Ein']),
        BsbFieldChoice(0x053D0D16, 2205, u'Bei Ökobetrieb', choices=['Aus', 'Nur Trinkwasser', 'Ein'], **RW),
        BsbFieldTemperature(0x0d3d092c, 2210, u'Sollwert Minimum', ),
        BsbFieldTemperature(0x0d3d092b, 2212, u'Sollwert Maximum', ),
        BsbFieldTemperature(0x0d3d08eb, 2214, u'Sollwert Handbetrieb', ),
        BsbField(0x093d2f98, 2440, u'Gebläse-PWM Hz Maximum', ),
        BsbField(0x0d3d2f94, 2441, u'Gebläsedrehzahl Hz Maximum', ),
        BsbField(0x193d2fbf, 2442, u'Gebläse-PWM Reglerverzög', ),
        BsbField(0x2d3d2fd4, 2443, u'Gebläse-PWM Startwert DLH', ),
        BsbField(0x093d3066, 2445, u'Leistung Nenn', ),
        BsbField(0x053d3076, 2446, u'Gebläseabschaltverzögerung', ),
        BsbField(0x093d2f9a, 2451, u'Brennerpausenzeit Minimum', ),
        BsbField(0x113d2f87, 2452, u'SD Brennerpause', ),
        BsbField(0x2d3d2f9b, 2453, u'Reglerverzögerung Dauer', ),
        BsbField(0x213d2f8c, 2454, u'Schaltdifferenz Kessel', ),
        BsbField(0x213d2f8d, 2455, u'Schaltdiff Kessel Aus Min', ),
        BsbField(0x213d2f8e, 2456, u'Schaltdiff Kessel Aus Max', ),
        BsbField(0x113d3051, 2471, u'Pumpennachlaufzeit HK\'s', ),
        BsbField(0x113d2f86, 2472, u'Pumpennachlauftemp TWW', ),
        BsbField(0x093d2f84, 2521, u'Frostschutz Einschalttemp', ),
        BsbField(0x093d2f85, 2522, u'Frostschutz Ausschalttemp', ),
    ]),
    
    Group(3800, "3800 Solar", [
        # Menü Solar
        BsbFieldTemperature(0x493D085D, 3810, u'Temperaturdifferenz EIN', min=4, max=40, **RW),
        BsbFieldTemperature(0x493D085C, 3811, u'Temperaturdifferenz AUS', min=0, max=8, **RW),
        BsbFieldTemperature(0x493D085A, 3812, u'Ladetemp Min TWW-Speicher', min=8, max=95, **RWN),
        # 3813: Telegram nicht decodierbar (bad CRC)
        # Code fuer 3814 oder 3815? - Fehler im Mitschnitt Grund: DC im Feld
        BsbFieldTemperature(0x493D0ADC, 3813, u'Temp\'differenz EIN Puffer', min=.5, max=50, **RWN),
        BsbFieldTemperature(0x493D0ADD, 3814, u'Temp\'differenz EIN Puffer', min=0, max=4, **RWN),
        BsbFieldTemperature(0x493D0A07, 3815, u'Ladetemp Min Puffer' , min=8, max=95, **RWN),
        BsbFieldTemperature(0x493D0ADE, 3816, u'Temp\'differenz EIN Sch\'bad', min=4, max=40, **RWN),
        BsbFieldTemperature(0x493D0ADF, 3817, u'Temp\'differenz AUS Sch\'bad', min=0, max=4, **RWN),
        BsbFieldTemperature(0x493D0AE7, 3818, u'Ladetemp Min Schwimmbad', min=8, max=95, **RWN),
        BsbFieldChoice(0x493D0AE3, 3822, u'Ladevorrang Speicher', choices=[
            u'Kein', 
            u'Trinkwasserspeicher', 
            u'Pufferspeicher'
        ], **RW),
        # FIXME:
        BsbFieldInt8(0x493D0AE0, 3825, u'Ladezeit relativer Vorrang', unit=u'min', tn="MINUTES_SHORT", min=2, max=60,  **RWN),
        BsbFieldInt8(0x493D0AE1, 3826, u'Wartezeit relativer Vorrang', unit=u'min', tn="MINUTES_SHORT", min=1, max=40,  **RW),
        BsbFieldInt8(0x493D0AE2, 3827, u'Wartezeit Parallelbetrieb', unit=u'min', tn="MINUTES_SHORT", min=8, max=40,  **RWN),
        BsbFieldInt16(0x493D0AEE, 3828, u'Verzögerung Sekundärpumpe', unit=u'sec', tn="SECONDS_WORD", min=0, max=600, **RW),
        BsbFieldInt8(0x493D0716, 3830, u'Kollektorstartfunktion', unit=u'min', tn="MINUTES_SHORT", min=5, max=60, **RWN),
        BsbFieldInt8(0x493D0719, 3831, u'Mindestlaufzeit Kollek\'pumpe', unit=u'sec', tn="SECONDS_SHORT", min=5, max=120, **RW),
        BsbFieldTime(0x493D0AE4, 3832, u'Kollektorstartfunktion ein', **RW),
        BsbFieldTime(0x493D0AE5, 3833, u'Kollektorstartfunktion aus', **RW),
        BsbFieldInt8(0x493D0B12, 3834, u'Kollektorstartfkt. Gradient', unit=u'min/°C', tn="GRADIENT_SHORT", min=1, max=20, **RWN),
        BsbFieldTemperature(0x493D0860, 3840, u'Kollektor Frostschutz', min=-20, max=5, **RWN),
        BsbFieldTemperature(0x493D0865, 3850, u'Kollektorüberhitzschutz', min=30, max=350, **RWN),
        BsbFieldTemperature(0x493D0551, 3860, u'Verdampfung Wärmeträger', min=60, max=350, **RWN),
        BsbFieldChoice(0x493D0509, 3880, u'Frostschutzmittel', choices=[
            u'',
            u'Kein',
            u'Ethylenglykol',
            u'Propylenglykol',
            u'Ethylen- und Propylenglykol',
        ], **RW),
        BsbFieldInt8(0x493D050A, 3881, u'Frost\'mittel Konzentration', unit=u'%', tn="PERCENT", min=1, max=100, **RW),
        BsbFieldInt16(0x493D050C, 3884, u'Pumpendurchfluss', unit=u'l/h', tn="LITERPERHOUR", min=10, max=1500, **RW),
        # Fehlinterpretiert
        #BsbFieldInt16(0x053D0F93, 3887, u'Impulseinheit Ertrag', unit=u'l', divisor=10.0, min=0, max=100, **RW),
    ]),
        
    Group(8000, u"8000 Status", [
        # FIXME: in the list with 0x053d07a4
        BsbFieldChoice(0x053d07a3, 8000, u'Status Heizkreis 1', choices=_choices_heizkreis),
        # FIXME: in the list with 0x053d07a6
        BsbFieldChoice(0x053d07a5, 8001, u'Status Heizkreis 2', choices=_choices_heizkreis),
        BsbFieldChoice(0x053d07a7, 8002, u'Status Heizkreis P', choices=_choices_heizkreis),
        # FIXME: logically it should be 0x053d07a1 but this works, too. maybe the last bit is ignored
        # or has another use?
        BsbFieldChoice(0x053d07a2, 8003, u'Status Trinkwasser', choices={
            0  : u'---',
            92 : u"Push, Legionellensollwert",
            93 : u"Push, Nennsollwert",
            94 : u"Push aktiv",
            95 : u"Ladung, Legionellensollwert",
            96 : u"Ladung, Nennsollwert",
            97 : u"Ladung, Reduziertsollwert",
            69 : u"Ladung aktiv",
            24 : u"Frostschutz aktiv",
            17 : u"Nachlauf aktiv",
            201: u"Bereitschaftsladung",
            70 : u"Geladen, Max Speichertemp",
            71 : u"Geladen, Max Ladetemp",
            98 : u"Geladen, Legio’temperatur",
            99 : u"Geladen, Nenntemperatur",
            100: u"Geladen, Reduz’temperatur",
            75 : u"Geladen",
            25 : u"Aus",
            200: u"Bereit",
        }),
        BsbFieldChoice(0x053d07a9, 8005, u'Status Kessel', choices={
            0  : u'---',
            1  : u'STB angesprochen',
            123: u'STB Test aktiv',
            2  : u'Störung',
            3  : u'Wächter angesprochen',
            4  : u'Handbetrieb aktiv',
            5  : u'Schornsteinfegerfkt, Vollast',
            6  : u'Schornsteinfegerfkt, Teillast',
            7  : u'Schornsteinfegerfkt aktiv',
            8  : u'Gesperrt, Manuell',
            172: u'Gesperrt, Feststoffkessel',
            9  : u'Gesperrt, Automatisch',
            176: u'Gesperrt, Außentemperatur',
            198: u'Gesperrt, Oekobetrieb',
            10 : u'Gesperrt',
            20 : u'Minimalbegrenzung',
            21 : u'Minimalbegrenzung, Teillast',
            22 : u'Minimalbegrenzung aktiv',
            11 : u'Anfahrentlastung',
            12 : u'Anfahrentlastung, Teillast',
            13 : u'Rückl’begrenzung',
            14 : u'Rückl’begrenzung, Teillast',
            18 : u'In Betrieb',
            59 : u'Ladung Pufferspeicher',
            170: u'In Betrieb für HK, TWW',
            171: u'In Teillastbetrieb für HK, TWW',
            173: u'Freigegeben für HK, TWW',
            168: u'In Betrieb für Trinkwasser',
            169: u'In Teillastbetrieb für TWW',
            174: u'Freigeben für TWW',
            166: u'In Betrieb für Heizkreis',
            167: u'In Teillastbetrieb für HK',
            175: u'Freigegeben für HK',
            17 : u'Nachlauf aktiv',
            19 : u'Freigegeben',
            23 : u'Anlagenfrostschutz aktiv',
            24 : u'Frostschutz aktiv',
            25 : u'Aus',
        }),
        # FIXME: also seen with 0x053d07ad ??
        BsbFieldChoice(0x053d07ae, 8007, u'Status Solar', choices={
            0  : u'---',
            4  : u"Handbetrieb aktiv",
            2  : u"Störung",
            52 : u"Kollektorfrostschutz aktiv",
            53 : u"Rückkühlung aktiv",
            54 : u"Max Speichertemp erreicht",
            55 : u"Verdampfungsschutz aktiv",
            56 : u"Überhitzschutz aktiv",
            57 : u"Max Ladetemp erreicht",
            151: u"Lad'ng TWW + Puffer + Sch'bad",
            152: u"Ladung Trinkwasser + Puffer",
            153: u"Ladung Trinkwasser + Sch'bad",
            154: u"Ladung Puffer + Schwimmbad",
            58 : u"Ladung Trinkwasser",
            59 : u"Ladung Pufferspeicher",
            60 : u"Ladung Schwimmbad",
            61 : u"Min Ladetemp nicht erreicht",
            62 : u"Temp’differenz ungenügend",
            63 : u"Einstrahlung ungenügend",
        }),
        BsbFieldChoice(0x053d0a08, 8008, u'Status Feststoffkessel', choices={
            0  : u'---',
            4  : u'Handbetrieb aktiv',
            2  : u'Störung',
            56 : u'Überhitzschutz aktiv',
            8  : u'Gesperrt, Manuell',
            9  : u'Gesperrt, Automatisch',
            10 : u'Gesperrt',
            20 : u'Minimalbegrenzung',
            21 : u'Minimalbegrenzung, Teillast',
            22 : u'Minimalbegrenzung aktiv',
            11 : u'Anfahrentlastung',
            12 : u'Anfahrentlastung, Teillast',
            13 : u'Rücklaufbegrenzung',
            14 : u'Rücklaufbegrenzung, Teillast',
            166: u'In Betrieb für Heizkreis',
            167: u'In Teillastbetrieb für HK',
            168: u'In Betrieb für Trinkwasser',
            169: u'In Teillastbetrieb für TWW',
            170: u'In Betrieb für HK, TWW',
            171: u'In Teillastbetrieb für HK, TWW',
            17 : u'Nachlauf aktiv',
            18 : u'In Betrieb',
            163: u'Anfeuerungshilfe aktiv',
            19 : u'Freigegeben',
            23 : u'Anlagenfrostschutz aktiv',
            141: u'Kesselfrostschutz aktiv',
            24 : u'Frostschutz aktiv',
            25 : u'Aus',
        }),
        # FIXME: Fehlt im ISR-Systemhandbuch (2009) -> Statuswerte nicht bekannt
        BsbFieldChoice(0x053d0f66, 8009, u'Status Brenner', choices={}),
        BsbFieldChoice(0x053D07AB, 8010, u'Status Pufferspeicher', choices={
            0: u'---',
            202: u'Frostschutz Kühlen aktiv',
            135: u'Sperrdauer nach Heizen',
            81 : u'Ladung gesperrt',
            124: u'Ladung eingeschränkt',
            67 : u'Zwangsladung aktiv',
            203: u'Durchladung aktiv',
            69 : u'Ladung aktiv',
            72 : u'Geladen, Zwangslad Solltemp',
            73 : u'Geladen, Solltemperatur',
            143: u'Geladen, Min Ladetemp',
            75 : u'Geladen',
            147: u'Warm',
            51 : u'Keine Anforderung',
            24 : u'Frostschutz aktiv',
            64 : u'Ladung Elektro, Notbetrieb',
            65 : u'Ladung Elektro, Quell’schutz',
            131: u'Ladung Elektro, Abtauen',
            164: u'Ladung Elektro, Zwang',
            165: u'Ladung Elektro, Ersatz',
            66 : u'Ladung Elektroeinsatz',
            81 : u'Ladung gesperrt',
            104: u'Eingeschränkt, TWW-Vorrang',
            124: u'Ladung eingeschränkt',
            67 : u'Zwangsladung aktiv',
            68 : u'Teilladung aktiv',
            69 : u'Ladung aktiv',
            77 : u'Rückkühlung via Kollektor',
            142: u'Rückkühlung via TWW / Hk’s',
            53 : u'Rückkühlung aktiv',
            70 : u'Geladen, Max Speichertemp',
            71 : u'Geladen, Max Ladetemp',
            72 : u'Geladen, Zwanglad Solltemp',
            73 : u'Geladen, Solltemperatur',
            74 : u'Teilgeladen, Solltemperatur',
            143: u'Geladen, Min Ladetemp',
            75 : u'Geladen',
            76 : u'Kalt',
            51 : u'Keine Wärmeanforderung',
        }),
        BsbFieldChoice(0x053d0afc, 8011, u'Status Schwimmbad', choices={
            0: u'---',
            4  : u'Handbetrieb aktiv',
            2  : u'Störung',
            106: u'Heizbetrieb eingeschränkt',
            110: u'Zwangsabnahme',
            155: u'Heizbetrieb Erzeuger',
            137: u'Heizbetrieb',
            156: u'Geheizt, Max Schw\'badtemp',
            158: u'Geheizt, Sollwert Solar',
            157: u'Geheizt, Sollwert Erzeuger',
            159: u'Geheizt',
            160: u'Heizbetrieb Solar aus',
            161: u'Heizbetrieb Erzeuger aus',
            162: u'Heizbetrieb aus',
            76 : u'Kalt',
        }),
    ]),
        

    
    Group(8300, u"8300 Diagnose Erzeuger", [
        # FIXME: Fehlt im ISR-Systemhandbuch (2009) -> Statuswerte nicht bekannt
        BsbFieldChoice(0x053d09a2, 8304, u'Kesselpumpe Q1', choices={
            255: u'Ein', # von LCD abgelesen
        }),
        BsbFieldInt8(0x053D0826, 8308, u'Drehzahl Kesselpumpe', unit='%', tn="PERCENT"),
        BsbFieldTemperature(0x0d3d0519, 8310, u'Kesseltemperatur', ),
        BsbFieldTemperature(0x0d3d0923, 8311, u'Kesselsollwert', ),
        # FIXME: Einheit nirgends zu finden -- geraten anhand Wert
        BsbFieldTemperature(0x053D0B26, 8312, u'Kesselschaltpunkt'),
        BsbFieldTemperature(0x113d051a, 8314, u'Kesselrücklauftemperatur', ),
        # FIXME: Divisor nicht bekannt
        BsbFieldInt16(0x093D0E69, 8323, u'Gebläsedrehzahl', unit='rpm', tn="SPEED2"),
        # FIXME: Divisor nicht bekannt
        BsbFieldInt16(0x093D0E6A, 8324, u'Brennergebläsesollwert', unit='rpm', tn="SPEED2"),
        # FIXME: Divisor nicht bekannt
        BsbFieldInt16(0x093D0E00, 8325, u'Akt. Gebläsesteuerung', unit='%', tn="PERCENT_WORD1"),
        BsbFieldInt8(0x053D0834, 8326, u'Brennermodulation', unit='%', tn="PERCENT"),
        # FIXME: Divisor nicht bekannt
        BsbFieldInt16(0x093D0E16, 8329, u'Ionisationsstrom', unit='uA', tn="CURRENT"),
        BsbFieldInt32(0x0D3D093B, 8330, u'Betriebsstunden 1. Stufe', **OP_HOURS),
        BsbFieldInt32(0x053D08A5, 8331, u'Startzähler 1. Stufe', tn="DWORD"),
        BsbFieldInt32(0x053D2FEB, 8338, u'Betriebsstunden Heizbetrieb', **OP_HOURS),
        BsbFieldInt32(0x053D2FEC, 8339, u'Betriebsstunden TWW', **OP_HOURS),
        BsbFieldInt8(0x093D0DFD, 8390, u'Aktuelle Phasennummer', tn="BYTE"),
    ]),
    
    Group(8400, u"8400 Diagnose Solar", [
        BsbFieldChoice(0x053D09AB, 8499, u'Kollektorpumpe 1 (Aus)', choices=['Aus', 'Ein']),
        # FIXME: Statuswerte unbekannt
        BsbFieldChoice(0x053D0A89, 8501, u'Solarstellglied Puffer', choices=[]),
        # FIXME: Statuswerte unbekannt
        BsbFieldChoice(0x053D0A8B, 8502, u'Solarstellglied Schwimmbad', choices=[]),
        BsbFieldTemperature(0x493d052a, 8510, u'Kollektortemperatur 1', ),
        BsbFieldTemperature(0x493d053f, 8511, u'Kollektortemperatur 1 max', ),
        BsbFieldTemperature(0x493d0718, 8512, u'Kollektortemperatur 1 min', ),
        BsbFieldTemperature(0x493d053b, 8512, u'dT Kollektor 1 / TWW', ),
        BsbFieldTemperature(0x493d053c, 8513, u'dT Kollektor 1 / Puffer', ),
        BsbFieldTemperature(0x493d042e, 8514, u'dT Kollektor 1 / Schwimmbad', ),
        BsbFieldTemperature(0x493d050e, 8519, u'Solarvorlauftemperatur', ),
        BsbFieldTemperature(0x493d050f, 8520, u'Solarrücklauftemperatur', ),
        # FIXME: Divisor geraten anhand Anzeige
        BsbFieldInt16(0x493D0599, 8526, u'Tagesertrag Solarenergie (kWh)', tn="ENERGY_WORD", divisor=10),
        # FIXME: Divisor nicht bekannt
        BsbFieldInt32(0x493D0598, 8527, u'Gesamtertrag Solarenergie (kWh)', tn="ENERGY_WORD"),
        BsbFieldInt32(0x493d0893, 8530, u'Betr\'stunden Solarertrag', **OP_HOURS),
        BsbFieldInt32(0x493d0717, 8531, u'Betr\'stunden Kollektorüberhitz', **OP_HOURS),
        BsbFieldInt32(0x053D10A5, 8532, u'Betr\'stunden Kollektorpumpe', **OP_HOURS),
        BsbFieldTemperature(0x513D052E, 8560, u'Feststoffkesseltemperatur'),
        BsbFieldInt32(0x513D0892, 8570, u'Betr\'stunden Feststoffkessel', **OP_HOURS),
   ]),
    
    Group(8700, u"8700 Diagnose Verbraucher", [
        BsbFieldTemperature(0x053d0521, 8700, u'Außentemperatur', ),
        BsbFieldTemperature(0x053d056f, 8701, u'Außentemperatur Minimum', ),
        BsbFieldTemperature(0x053d056e, 8702, u'Außentemperatur Maximum', ),
        BsbFieldTemperature(0x053d05f0, 8703, u'Außentemperatur gedämpft', ),
        BsbFieldTemperature(0x053d05f2, 8704, u'Außentemperatur gemischt', ),
        # FIXME: wert 255 aus tats. Telegram
        BsbFieldChoice(0x053D09A5, 8730, u'Heizkreispumpe 1', choices={0:'Aus', 1:'Ein', 255:'Ein'}),
        BsbFieldChoice(0x053D09A6, 8731, u'Heizkreismischer 1 Auf', choices=['Aus', 'Ein']),
        BsbFieldChoice(0x053D09A7, 8732, u'Heizkreismischer 1 Zu', choices=['Aus', 'Ein']),
        BsbFieldInt8(0x213D04A7, 8735, u'Drehzahl Heizkreispumpe 1', unit='%', tn="PERCENT1"),
        BsbFieldTemperature(0x2d3d051e, 8740, u'Raumtemperatur 1', ),
        BsbFieldTemperature(0x2d3d0593, 8741, u'Raumsollwert 1', ),
        BsbFieldTemperature(0x213d0518, 8743, u'Vorlauftemperatur 1', ),
        BsbFieldTemperature(0x213d0667, 8744, u'Vorlaufsollwert 1', ),
        BsbFieldChoice(0x053D0C7D, 8749, u'Raumthermostat 1', choices=[]),
        BsbFieldChoice(0x053D09A8, 8760, u'Heizkreispumpe 2', choices={0:'Aus', 1:'Ein', 255:'Ein'}),
        BsbFieldChoice(0x053D09A9, 8761, u'Heizkreismischer 2 Auf', choices=['Aus', 'Ein']),
        BsbFieldChoice(0x053D09AA, 8762, u'Heizkreismischer 2 Zu', choices=['Aus', 'Ein']),
        BsbFieldInt8(0x223D04A7, 8765, u'Drehzahl Heizkreispumpe 2', unit='%', tn="PERCENT1"),
        BsbFieldTemperature(0x2e3d051e, 8770, u'Raumtemperatur 2', ),
        BsbFieldTemperature(0x2e3d0593, 8771, u'Raumsollwert 2', ),
        BsbFieldTemperature(0x223d0518, 8773, u'Vorlauftemperatur 2', ),
        BsbFieldTemperature(0x223d0667, 8774, u'Vorlaufsollwert 2', ),
        BsbFieldChoice(0x063D0C7D, 8779, u'Raumthermostat 2', choices=[]),
        BsbFieldChoice(0x053D09B0, 8790, u'Heizkreispumpe 3', choices={0:'Aus', 1:'Ein', 255:'Ein'}),
        BsbFieldChoice(0x053D0AA7, 8791, u'Heizkreismischer 3 Auf', choices=['Aus', 'Ein']),
        BsbFieldChoice(0x053D0AA8, 8792, u'Heizkreismischer 3 Zu', choices=['Aus', 'Ein']),
        BsbFieldInt8(0x233D04A7, 8795, u'Drehzahl Heizkreispumpe 3', unit='%', tn="PERCENT1"),
        BsbFieldTemperature(0x313d052f, 8830, u'Trinkwassertemperatur 1', ),
        BsbFieldTemperature(0x313d0530, 8832, u'Trinkwassertemperatur 2',),
   ]),
        
    Group(0, "Unsortiert", [
        # weitere (nicht verifizierte) Eintraege
        BsbField(0x2d3d0215, 10109, u'Senden Raumtemperatur', ),
        BsbField(0x2d000211, 10102, u'HK1 - TBD', ),
        BsbField(0x2e3e0574, 10112, u'Heizbetrieb', ),
        BsbField(0x2e000211, 10103, u'HK2 - TBD', ),
        BsbField(0x313D0721, 1630, u'Trinkwasser Ladevorrang', ),
        BsbField(0x313d3009, 5019, u'Nachlad\'Übserhöh Schichtensp', ),
        BsbField(0x313d074b, 8831, u'Trinkwassersollwert', ),
        BsbField(0x2e3d3073, 5971, u'Konfig Raumthermostat 2', ),
        BsbField(0x2e3d068a, 1151, u'Estrich Sollwert manuell', ),
        BsbField(0x2e3d067b, 1150, u'Estrich-Funktion', ),
        BsbField(0x2e3d0640, 1032, u'Tagesheizgrenze', ),
        BsbField(0x2e3d0614, 1060, u'Raumtemperaturbegrenzung', ),
        BsbField(0x2e3d0610, 1021, u'Kennlinie Verschiebung', ),
        BsbField(0x2e3d060b, 1026, u'Kennlinie Adaption', ),
        BsbField(0x2e3d0609, 1091, u'Ausschalt-Optimierung Max', ),
        BsbField(0x2e3d0607, 1090, u'Einschalt-Optimierung Max', ),
        BsbField(0x2e3d0603, 1050, u'Raumeinfluss', ),
        BsbField(0x2e3d0602, 1070, u'Schnellaufheizung', ),
        BsbField(0x2e3d05fd, 1030, u'Sommer-/Winterheizgrenze', ),
        BsbField(0x2e3d05f6, 1020, u'Kennlinie Steilheit', ),
        BsbField(0x2e3d05e8, 1080, u'Schnellabsenkung', ),
        BsbField(0x2e3d059e, 1100, u'Reduziert-Anhebung Beginn', ),
        BsbField(0x2e3d059d, 1101, u'Reduziert-Anhebung Ende', ),
        BsbField(0x2e3d0592, 1014, u'Frostschutzsollwert', ),
        BsbField(0x2e3d0590, 1012, u'Reduziertsollwert', ),
        BsbField(0x2e3d058e, 1010, u'Komfortsollwert', ),
        BsbField(0x2e3d04c2,  658, u'Betriebsniveau', ),
        BsbField(0x2d3d3073, 5970, u'Konfig Raumthermostat 1', ),
        BsbField(0x2d3d304c, 9540, u'Nachlüftzeit', ),
        BsbField(0x2d3d3037, 9500, u'Vorlüftzeit', ),
        BsbField(0x2d3d300c, 7051, u'Meldung Ion Strom', ),
        BsbField(0x2d3d2fea, 5701, u'Hydraulisches Schema', ),
        BsbField(0x2d3d2fda, 7007, u'Anzeige/Reset Meldungen.0', ),
        BsbField(0x2d3d2fd9, 7010, u'Quittierung Meldung', ),
        BsbField(0x2d3d2fd8, 7050, u'Gebläsedrehzahl Ion Strom', ),
        BsbField(0x2d3d2fd6, 7042, u'Brennerstarts Intervall', ),
        BsbField(0x2d3d04c2, 648, u'Betriebsniveau', ),
        BsbField(0x253d2fe9, 9563, u'Solldrehzahl Durchlasung', ),
        BsbField(0x253d2fe8, 9560, u'Gebl\'ansteuerung Durchlad', ),
        BsbField(0x253d2fdf, 7043, u'Brennerstarts seit Wartung', ),
        BsbField(0x253d2fdd, 7011, u'Repetitionszeit Meldung', ),
        BsbField(0x253d2f9f, 6250, u'KonfigRg2.x', ),
        BsbFieldTemperature(0x253d0b33, 8836, u'TWW Ladetemperatur', ),
        BsbFieldTemperature(0x253d08bd, 5055, u'Rückkühltemperatur',),
        BsbFieldTemperature(0x253d08a3, 5050, u'Ladetemperatur Maximum', ),
        BsbField(0x253d0720, 5020, u'Vorlaufsollwerterhöhung', ),
        BsbField(0x223d069d, 6741, u'Vorlauftemperatur 2 Alarm', ),
        BsbField(0x223d0663, 1040, u'Vorlaufsollwert Minimum', ),
        BsbField(0x223d0662, 1041, u'Vorlaufsollwert Maximum', ),
        BsbField(0x223d065d, 1130, u'Mischerüberhöhung', ),
        BsbField(0x223d065a, 1134, u'Antrieb Laufzeit', ),
        BsbField(0x213d3038, 9502, u'Gebl\'ansteuerung Vorlüftung', ),
        BsbField(0x213d300f, 9504, u'Solldrehzahl Vorlüftung', ),
        BsbField(0x213d2fd5, 5028, u'Schaltdifferenz 2 Aus min', ),
        BsbField(0x213d2f93, 5029, u'Schaltdifferenz 2 Aus max', ),
        BsbField(0x213d2f92, 5027, u'Schaltdifferenz 2 ein', ),
        BsbField(0x213d2f91, 5026, u'Schaltdifferenz 1 Aus max', ),
        BsbField(0x213d2f90, 5025, u'Schaltdifferenz 1 Aus min', ),
        BsbField(0x213d2f8f, 5024, u'Schaltdifferenz 1 ein', ),
        BsbField(0x193d2fdc, 5761, u'Zonen mit Zubringerpumpe', ),
        BsbField(0x193d2f8a, 894, u'dT Spreizung NormAussent', ),
        BsbField(0x193d2f88, 886, u'Norm Aussentemperatur', ),
        BsbField(0x153d3064, 6260, u'KonfigRg3.x', ),
        BsbField(0x153d2fcc, 5920, u'Relaisausgang K2 LMU-Basis', ),
        BsbField(0x153d2fa4, 6300, u'KonfigRg7.x', ),
        BsbField(0x153d2fa3, 6290, u'KonfigRg6.x', ),
        BsbField(0x153d2fa2, 6280, u'KonfigRg5.x', ),
        BsbField(0x153d2fa1, 6270, u'KonfigRg4.x', ),
        BsbField(0x153d2f9e, 6240, u'KonfigRg1.x', ),
        BsbField(0x153d2f9d, 6230, u'KonfigRg0.x', ),
        BsbField(0x113d304f, 885, u'Pumpe-PWM Minimum', ),
        BsbField(0x113d2fe4, 5733, u'TWW Pum\'pause Verzögerung', ),
        BsbField(0x113d2fe3, 5732, u'TWW Pumpenpause Umsch UV', ),
        BsbField(0x113d2fb4, 6127, u'Pumpen/Ventilkick Dauer', ),
        BsbField(0x113d2f96, 5100, u'Pumpe-PWM Durchladung', ),
        BsbField(0x113d2f95, 884, u'DrehzahlstufeAusleg\'punkt', ),
        BsbField(0x0d3d304a, 9522, u'Gebl\'ansteuerung Betrieb. Max', ),
        BsbField(0x0d3d3049, 9520, u'Gebl\'ansteuerung Betrieb. Min', ),
        BsbField(0x0d3d3048, 9510, u'Gebl\'ansteuerung Zündung', ),
        BsbField(0x0d3d3017, 6330, u'KonfigRg10.x', ),
        BsbField(0x0d3d2fcb, 9527, u'Solldrehzahl Betrieb Max', ),
        BsbField(0x0d3d2fca, 9524, u'Solldrehzahl Betrieb Min', ),
        BsbField(0x0d3d2fc9, 9512, u'Solldrehzahl Zündung', ),
        BsbField(0x0d3d092a, 7130, u'Schornsteinfegerfunktion', ),
        BsbField(0x093d3072, 6705, u'SW Diagnosecode', ),
        BsbField(0x093d3054, 5978, u'Funktion Eingang SolCl', ),
        BsbField(0x093d3036, 8336, u'Betriebsstunden Brennner', ),
        BsbField(0x093d3035, 8337, u'Startzähler Brenner', ),
        BsbField(0x093d3034, 8328, u'Betriebsanzeige FA', ),
        BsbField(0x093d3033, 6221, u'Entwicklungs-Index', ),
        BsbField(0x093d3022, 7145, u'Reglerstopp Sollwert', ),
        BsbField(0x093d3021, 7143, u'Reglerstoppfunktion', ),
        BsbField(0x073d0a8c, 540, u'Vorwahl / Phasen', ),
        BsbField(0x073d05b2, 556, u'Standardwerte', ),
        BsbField(0x063d0a8c, 520, u'Vorwahl / Phasen', ),
        BsbField(0x063d09c5, 653, u'Ende', ),
        BsbField(0x063d09c4, 652, u'Beginn', ),
        BsbField(0x063d05b2, 536, u'Standardwerte', ),
        BsbField(0x063d04c0, 5715, u'Heizkreis 2', ),
        BsbField(0x053d3078, 5921, u'Parameter', ),
        BsbField(0x053d3050, 887, u'Vorlaufsoll NormAussemtemp', ),
        BsbField(0x053d3002, 6845, u'SW Diagnosecode 5', ),
        BsbField(0x053d3001, 6840, u'Historie 5', ),
        BsbField(0x053d2ffe, 6835, u'SW Diagnosecode 4', ),
        BsbField(0x053d2ffd, 6830, u'Historie 4', ),
        BsbField(0x053d2ffb, 6825, u'SW Diagnosecode 3', ),
        BsbField(0x053d2ff9, 6820, u'Historie 3', ),
        BsbField(0x053d2ff7, 6815, u'SW Diagnosecode 2', ),
        BsbField(0x053d2ff5, 6810, u'Historie 2', ),
        BsbField(0x053d2ff3, 6805, u'SW Diagnosecode 1', ),
        BsbField(0x053d0aa0, 560, u'Vorwahl / Phasen', ),
        BsbField(0x053d0a8c, 500, u'Vorwahl', ),
        BsbField(0x053d09c5, 643, u'Ende', ),
        BsbField(0x053d09c4, 642, u'Beginn', ),
        BsbField(0x053d06dd, 6800, u'Historie 1', ),
        BsbField(0x053d0600, 6110, u'Zeitkonstante Gebäude', ),
        BsbField(0x053d05fe, 6120, u'Anlagenfrostschutz', ),
        BsbField(0x053d05e2, 7045, u'Zeit seit Wartung', ),
        BsbField(0x053d05e1, 7044, u'Wartungsintervall', ),
        BsbField(0x053d05b3, 576, u'Standardwerte', ),
        BsbField(0x053d05b2, 516, u'Standardwerte', ),
        BsbFieldTemperature(0x053d0534, 8980, u'Pufferspeichertemperatur 1', ),
        BsbField(0x053d04c0, 5710, u'Heizkreis 1', ),
        BsbField(0x053d04a2, 8750, u'Mod Pumpe Sollwert', ),
        BsbField(0x053d0483, 5957, u'BA-Umschaltung HK\'s+TWW', ),
        BsbField(0x053d03f3, 7041, u'Brennerstd seit Wartung', ),
        BsbField(0x053d03f1, 7040, u'Brennerstunden Intervall', ),
        BsbField(0x053d0099, 10104, u'SW Diagnosecode', ),
        BsbField(0x053d0090, 7001, u'Meldung', ),
        BsbField(0x053d0075, 7140, u'Handbetrieb', ),
        BsbField(0x053d000e, 6220, u'Software-Version', ),
        BsbField(0x053d0004, 6227, u'Objektverzeichnis-Version', ),
        BsbField(0x053d0003, 6226, u'Gerätevariante', ),
        BsbField(0x053d0002, 6225, u'Gerätefamilie', ),
        BsbField(0x05000213, 10100, u'Brenner', ),
        BsbField(0x0500006c, 10101, u'Zeit', ),
    ]),
]

_all = it.chain(*[g.fields for g in groups])

fields = {f.disp_id: f for f in _all}
fields_by_telegram_id = {f.telegram_id: f for f in fields.values()}
fields_by_disp_id = fields
