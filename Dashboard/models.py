"""
Appraise evaluation framework

See LICENSE for usage details
"""
from uuid import uuid4

from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.db import models
from django.db.utils import OperationalError
from django.db.utils import ProgrammingError

# pylint: disable=import-error

LANGUAGE_CODES_AND_NAMES = {
    'aeb': 'Tunisian Arabic (تونسي)',
    'ces': 'Czech (čeština)',
    'zho': 'Chinese (中文)',
    'eng': 'English',
    'fin': 'Finnish (suomi)',
    'deu': 'German (Deutsch)',
    'lav': 'Latvian (latviešu)',
    'rus': 'Russian (русский)',
    'trk': 'Turkish (Türkçe)',
    'fra': 'French (français)',
    'hun': 'Hungarian (magyar)',
    'plk': 'Polish (polski)',
    'por': 'Portuguese (português)',
    'ron': 'Romanian (română)',
    'spa': 'Spanish (español)',
    'swe': 'Swedish (svenska)',
    'ara': 'Arabic (العربية)',
    'ita': 'Italian (italiano)',
    'jpn': 'Japanese (日本語)',
    'kor': 'Korean (한국어)',
    'nob': 'Norwegian (Bokmål)',
    'nld': 'Dutch (Nederlands)',
    'cat': 'Catalan (català)',
    'dan': 'Danish (dansk)',
    'hin': 'Hindi (हिन्दी)',
    'tha': 'Thai (ภาษาไทย)',
    'ben': 'Bengali (বাংলা)',
    'slk': 'Slovak (slovenčina)',
    'slv': 'Slovenian (slovenščina)',
    'est': 'Estonian (eesti)',
    'bul': 'Bulgarian (български)',
    'ell': 'Greek (ελληνικά)',
    'heb': 'Hebrew (עברית)',
    'cym': 'Welsh (Cymraeg)',
    'ukr': 'Ukrainian (українська)',
    'tel': 'Telugu (తెలుగు)',
    'tam': 'Tamil (தமிழ்)',
    'isl': 'Icelandic (íslenska)',
    'hrv': 'Croatian (hrvatski)',
    'lit': 'Lithuanian (lietuvių)',
    'vie': 'Vietnamese (tiếng Việt)',
    'srp': 'Serbian (srpski)',
    'bos': 'Bosnian (bosanski)',
    'ind': 'Indonesian (bahasa Indonesia)',
    'urd': 'Urdu (اُردُو)',
    'acm': 'Iraqi Arabic (راقي - ʕirāgi)',
    'ary': 'Moroccan Arabic (الدارجة - Darija)',
    'ayl': 'Libyan Arabic ( ليبي - lībi)',
    'ayn': 'Yemeni Arabic (يمني - yamani)',
    'fas': 'Farsi (فارسی)',
    'afr': 'Afrikaans',
    'mlt': 'Maltese (Malti)',
    'sin': 'Sinhalese (සිංහල sinhala)',
    'smo': 'Samoan (Gagana faʻa Sāmoa)',
    'mlg': 'Malagasy',
    'swa': 'Swahili (Kiswahili)',
    'fij': 'Fijian (Na Vosa Vakaviti)',
    'ton': 'Tongan (lea faka-Tonga)',
    'guj': 'Gujarati (ગુજરાતી)',
    'kaz': 'Kazakh (қазақша)',
    'zsm': 'Malaysian (bahasa Malaysia)',
    'hat': 'Haitian Creole (kreyòl ayisyen)',
    'fil': 'Filipino (Wikang Filipino)',
    'tah': 'Tahitian (Reo Tahiti)',
    'mri': 'Maori (Te reo Māori)',
    'pan': 'Punjabi (ਪੰਜਾਬੀ)',
    'kan': 'Kannada (ಕನ್ನಡ)',
    'mal': 'Malayalam (മലയാളം)',
    'mar': 'Marathi (मराठी)',
    'kat': 'Georgian (ქართული)',
    'gle': 'Irish (Gaeilge)',
    'zho-Hans': 'Simplified Chinese (中文 - 简化字)',
    'zho-Hant': 'Traditional Chinese (中文 - 正體字/繁體字)',
    'srp-Cyrl': 'Serbian (српски)',
    'srp-Latn': 'Serbian (srpski)',
    'asm': 'Assamese (অসমীয়া)',
    'ori': 'Odia (ଓଡ଼ିଆ)',
    'aze': 'Azerbaijani (Azeri)',
    'amh': 'Amharic (አማርኛ)',
    'sqi': 'Albanian (shqip)',
    'jav': 'Javanese (ꦧꦱꦗꦮ)',
    'sun': 'Sundanese (Basa Sunda)',
    'hau': 'Hausa (Harshen/Halshen Hausa)',
    'glg': 'Galician (galego)',
    'mya': 'Myanmar (မြန်မာစာ)',
    'ceb': 'Cebuano (Bisayâ)',
    'bel': 'Belarusian (беларуская мова)',
    'xho': 'Xhosa (isiXhosa)',
    'uzb': 'Uzbek (o‘zbekcha)',
    'ltz': 'Luxembourgish (Lëtzebuergesch)',
    'lao': 'Lao (ພາສາລາວ)',
    'khm': 'Khmer (ភាសាខ្មែរ)',
    'eus': 'Basque (euskara)',
    'hye': 'Armenian (հայերեն hayeren)',
    'mon': 'Mongolian (монгол хэл)',
    'mkd': 'Macedonian (македонски)',
    'som': 'Somali (Af Soomaali)',
    'tgk': 'Tajik (тоҷикӣ)',
    'kir': 'Kyrgyz (кыргыз)',
    'yid': 'Yiddish (ייִדיש)',
    'gla': 'Scottish Gaelic (Gàidhlig)',
    'epo': 'Esperanto',
    'lat': 'Latin (lingua latīna)',
    'yor': 'Yoruba (Èdè Yorùbá)',
    'zul': 'Zulu (isiZulu)',
    'ibo': 'Igbo (Asụsụ Igbo)',
    'tat': 'Tatar (татар теле)',
    'snd': 'Sindhi (سنڌي)',
    'nya': 'Chichewa (Nyanja)',
    'fry': 'Frisian (Frysk)',
    'sna': 'Shona (chiShona)',
    'bak': 'Bashkir (Башҡортса)',
    'prs': 'Dari (دری)',
    'haw': 'Hawaiian (ʻŌlelo Hawaiʻi)',
    'sot': 'Sotho (Sesotho)',
    'mhr': 'Meadow Mari (олыкмарла)',
    'pap': 'Papiamento (Papiamentu)',
    'udm': 'Udmurt (удмурт кыл)',
    'cos': 'Corsican (corsu)',
    'mrj': 'Hill Mari (Кырык мары йӹлмӹ)',
    'uig': 'Uyghur (ئۇيغۇر تىلى)',
    'wuu': 'Wu (吴语)',
    'pcm': 'Nigerian Pidgin',
    'tuk': 'Turkmen (Türkmençe)',
    'srd': 'Sardinian (sardu)',
    'hak': 'Hakka (客家话)',
    'hsn': 'Xiang (湘语)',
    'orm': 'Oromo (Afaan Oromoo)',
    'tsn': 'Tswana (Setswana)',
    'bew': 'Betawi (bahasa Betawi)',
    'gan': 'Gan (赣语)',
    'kin': 'Rwanda (Ikinyarwanda)',
    'shi': 'Shilha (ⵜⴰⵛⵍⵃⵉⵢⵜ)',
    'ace': 'Acehnese (Basa Acèh)',
    'quc': "K'iche' (Qatzijobʼal)",
    'ssw': 'Swazi (siSwati)',
    'ast': 'Asturian (asturianu)',
    'iku': 'Inuktitut (ᐃᓄᒃᑎᑐᑦ)',
    'bre': 'Breton (brezhoneg)',
    'oji': 'Ojibwe (Anishinaabemowin)',
    'hsb': 'Upper Sorbian (hornjoserbšćina)',
    'chr': 'Cherokee (ᏣᎳᎩ ᎦᏬᏂᎯᏍᏗ)',
    'lkt': 'Lakota (Lakȟótiyapi)',
    'ikt': 'Inuinnaqtun',
    'qwe': 'Quechua (Runasimi)',
    'tir': 'Tigrinya (ትግርኛ)',
    'wol': 'Wolof',
    'ewe': 'Ewe (Èʋegbe)',
    'fuc': 'Pulaar (Futa Tooro)',
    'bem': 'Bemba (Chibemba)',
    'mey': 'Hassaniya (حسانية)',
    'kok': 'Konkani (कोंकणी)',
    'nde': 'Ndebele (isiNdebele saseNyakatho)',
    'ven': 'Tshivenda (Tshivenḓa)',
    'bod': 'Tibetan (བོད་སྐད)',
    'oss': 'Ossetian (ирон ӕвзаг)',
    'ble': 'Balanta',
    'sag': 'Sango (yângâ tî sängö)',
    'div': 'Dhivehi (ދިވެހި)',
    'ogb': 'Ogbia (Ogbinya)',
    'dzo': 'Dzongkha (རྫོང་ཁ་)',
    'tpi': 'Tok Pisin',
    'oci': "Occitan (lenga d'òc)",
    'crs': 'Seychellois Creole (kreol, seselwa)',
    'fao': 'Faroese (føroyskt mál)',
    'amu': 'Amuzgo (Ñomndaa)',
    'agr': 'Aguaruna (Awajún)',
    'jiv': 'Shuar (Šiwar čičam)',
    'axk': 'Aka (Yaka)',
    'sme': 'Northern Sami (davvisámegiella)',
    'ppk': 'Uma (Pipikoro)',
    'arg': 'Aragonese (aragonés)',
    'bis': 'Bislama (Bichelamar)',
    'dsb': 'Lower Sorbian (dolnoserbšćina)',
    'acu': 'Achuar (Shiwiar)',
    'soq': 'Sona (Kanasi)',
    'usp': 'Uspantek (Uspanteco)',
    'bbg': 'Barama (Varama)',
    'kmr': 'Kurmanji (Kurmancî)',
    'ckb': 'Sorani (کوردیی ناوەندی)',
    'nep': 'Nepali (नेपाली)',
    'yue': 'Cantonese (廣東話)',
    'apc': 'Levantine Arabic (اللَّهْجَةُ الشَّامِيَّة)',
    'arz': 'Egyptian Arabic (اللهجه المصريه)',
    'afb': 'Gulf Arabic (خليجي)',
    'mww': 'Hmong Daw',
    'otq': 'Querétaro Otomi',
    'tlh': 'Klingon (tlhIngan Hol)',
    'yua': 'Yucatec Maya (mayaʼ tʼàan)',
    'pus': 'Pashto (پښتو)',
    'lzh': 'Classical Chinese (文言文)',
    'chv': 'Chuvash (Чӑвашла)',
    'lin': 'Lingala (Lingála)',
    'lug': 'Luganda (Oluganda)',
    'sgg': 'Swiss-German Sign Language (Deutschschweizer Gebärdensprache (DSGS))',
    'liv': 'Livonian (līvõ kēļ)',
    'sah': 'Yakut (саха тыла)',
}

# All sign language codes
SIGN_LANGUAGE_CODES = set([LANGUAGE_CODES_AND_NAMES['sgg']])

# Ensure that all languages have a corresponding group.
try:
    for code in LANGUAGE_CODES_AND_NAMES:
        if not Group.objects.filter(name=code).exists():
            new_language_group = Group(name=code)
            new_language_group.save()

except (OperationalError, ProgrammingError):
    pass


def validate_language_code(code_or_codes):
    """
    Validates given language code string or list of code strings.

    Returns True if valid, False otherwise.
    """
    valid_codes = [x.lower() for x in LANGUAGE_CODES_AND_NAMES]
    valid = False
    if isinstance(code_or_codes, (list, tuple)):
        valid = all([x.lower() in valid_codes for x in code_or_codes])

    else:
        valid = code_or_codes.lower() in valid_codes

    return valid


def create_uuid4_token():
    """
    Creates a new UUID4-based token.
    """
    return uuid4().hex[:8]


# pylint: disable=C0330,E1101,too-few-public-methods
class UserInviteToken(models.Model):
    """
    User invite tokens allowing to register an account.
    """

    group = models.ForeignKey(Group, models.PROTECT, db_index=True)

    user = models.ForeignKey(User, models.PROTECT, db_index=True, blank=True, null=True)

    token = models.CharField(
        max_length=8,
        db_index=True,
        default=create_uuid4_token,
        unique=True,
        help_text="Unique invite token",
        verbose_name="Invite token",
    )

    active = models.BooleanField(
        db_index=True,
        default=True,
        help_text="Indicates that this invite can still be used.",
        verbose_name="Active?",
    )

    class Meta:
        """
        Metadata options for the UserInviteToken object model.
        """

        verbose_name = "User invite token"
        verbose_name_plural = "User invite tokens"

    def __str__(self):
        """
        Returns a Unicode String for this UserInviteToken object.
        """
        return u'<user-invite id="{0}" token="{1}" active="{2}" group="{3}" />'.format(
            self.id, self.token, self.active, self.group.name
        )


# pylint: disable=too-few-public-methods
class TimedKeyValueData(models.Model):
    """
    Stores a simple (key, value) pair.
    """

    key = models.CharField(max_length=100, blank=False, null=False)
    value = models.TextField(blank=False, null=False)
    date_and_time = models.DateTimeField(
        blank=False, null=False, editable=False, auto_now_add=True
    )

    @classmethod
    def update_status_if_changed(cls, key, new_value):
        """
        Stores a new TimedKeyValueData instance if value for key has changed
        """
        _latest_values = cls.objects.filter(key=key)
        _latest_values = _latest_values.order_by('date_and_time').reverse()
        _latest_values = _latest_values.values_list('value', flat=True)
        if not _latest_values or _latest_values[0] != new_value:
            new_data = cls(key=key, value=new_value)
            new_data.save()
