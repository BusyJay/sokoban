from HTMLParser import HTMLParser
from cStringIO import StringIO
from collections import deque
from bs4 import BeautifulSoup, Comment, Doctype, Tag, NavigableString
from bs4.dammit import EntitySubstitution
from bs4.element import AttributeValueWithCharsetSubstitution

__author__ = 'jay'

ALLOWED_TAGS = {'html', 'head', 'meta', 'title', 'body', 'div', 'p', 'h1',
                'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'a', 'img', 'table',
                'tbody', 'th', 'tr', 'td', 'blockquote', 'pre', 'code', 'sub',
                'sup', 'ul', 'li', 'ol', 'em', 'strong', 'u', 'small', 'big',
                "dt", "dl", "dd"}

# following tag will be replace with its content
MERCiFUL_TAG = {'tt'}


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class RawHtmlParser(object):
    """
    !!! not thread safe
    """
    def __init__(self, must_handle):
        self.must_handle = must_handle
        self.dom = StringIO()

    def feed(self, data):
        # truncate first to save memory
        self.dom.truncate(0)
        # for python3 compatibility
        self.dom.seek(0)
        soup = BeautifulSoup(data, 'html5lib')

        # since soup() is not a generator, it should be fine to iterate and
        #  edit

        # handle code block
        for div in soup.select('div[class^=highlight-]'):
            self.handle_highlight(div, soup)

        # kill useless navigation
        for div in soup.select('div.related'):
            for child in div.children:
                if child.name in ['h1', 'h2', 'h3', 'h4', 'h5']:
                    if child.text == 'Navigation':
                        div.decompose()
                        break

        # kill table of content navigation
        for div in soup.select('div.sphinxsidebarwrapper'):
            for child in div.children:
                if child.name in ['h1', 'h2', 'h3', 'h4', 'h5']:
                    if child.text == 'Table Of Contents':
                        div.decompose()
                        break

        # filter and edit tags
        for tag in soup():
            if tag.name not in ALLOWED_TAGS:
                if tag.name in MERCiFUL_TAG:
                    tag.replace_with_children()
                    continue
                tag.decompose()
                continue
            final_attr = dict()
            if tag.has_attr('id'):
                final_attr['id'] = tag['id']
            if tag.has_attr('style'):
                final_attr['style'] = tag['style']

            result = getattr(self, 'handle_' + tag.name,
                             self.handle_default)(tag, final_attr)
            if result is False:
                tag.decompose()
                continue
            elif result is True:
                continue
            tag.attrs.clear()
            tag.attrs.update(final_attr)

        self.output_dom(soup.html)
        self.dom.seek(0)
        soup.decompose()

    def output_dom(self, tag):
        attrs = []
        if tag.attrs:
            for key, val in tag.attrs.iteritems():
                if val is None:
                    decoded = key
                else:
                    if isinstance(val, list) or isinstance(val, tuple):
                        val = ' '.join(val)
                    elif not isinstance(val, basestring):
                        val = unicode(val)
                    elif isinstance(val,
                                    AttributeValueWithCharsetSubstitution):
                        val = val.encode('utf-8')

                    text = tag.format_string(val)
                    decoded = (
                        unicode(key) + '='
                        + EntitySubstitution.quoted_attribute_value(text))
                attrs.append(decoded)
        close = ''
        close_tag = ''

        if tag.is_empty_element:
            close = '/'
        else:
            close_tag = '</%s>' % tag.name
        attribute_string = ''
        if attrs:
            attribute_string = ' ' + ' '.join(attrs)
        self.dom.write('<%s%s%s>' % (tag.name, attribute_string, close))
        is_visible_string = lambda s: (isinstance(s, NavigableString) and
                                       not isinstance(s, Comment))
        if tag.contents:
            has_print = False
            if tag.name == 'pre':
                self.dom.write(tag.encode_contents(encoding='utf-8'))
            elif len(tag.contents) == 1:
                sub_tag = tag.contents[0]
                if isinstance(sub_tag, Tag):
                    if not has_print:
                        self.dom.write('\n')
                        has_print = True
                    self.output_dom(sub_tag)
                elif is_visible_string(sub_tag):
                    self.dom.write(sub_tag.output_ready(formatter='html')
                                   .strip().encode('utf-8'))
            else:
                for sub_tag in tag.contents:
                    if isinstance(sub_tag, Tag):
                        if not has_print:
                            self.dom.write('\n')
                            has_print = True
                        self.output_dom(sub_tag)
                    elif is_visible_string(sub_tag) and not sub_tag.isspace():
                        prefix = postfix = ''
                        if sub_tag[0].isspace():
                            prefix = ' '
                        if sub_tag[-1].isspace():
                            postfix = ' '
                        self.dom.write(
                            prefix + sub_tag.output_ready(formatter='html')
                            .strip().encode('utf-8') + postfix)
        self.dom.write(close_tag)
        self.dom.write('\n')

    def read(self, size=-1):
        return self.dom.read(size)

    def handle_highlight(self, tag, soup):
        hl_lang = filter(lambda cls: cls.startswith('highlight-'),
                         tag['class'])[0]
        lang = hl_lang[10:]
        code_block = soup.new_tag('pre')
        code_block['data-lang'] = lang
        code_block.append(soup.new_string(tag.pre.get_text()))

        tag.replace_with(code_block)

    def handle_span(self, tag, final_attr):
        if 'pre' not in tag.attrs.get('class', []) or not final_attr:
            # a pure span is meaningless
            tag.replace_with_children()
            return True
        final_attr['data-type'] = 'keyword'

    def handle_pre(self, tag, final_attr):
        if tag.has_attr('data-lang'):
            final_attr['data-lang'] = tag['data-lang']

    def handle_a(self, tag, final_attr):
        href = tag.attrs.get('href', '#')
        if not self.must_handle(href):
            href = '#'
        final_attr['href'] = href
        if tag.has_attr('target'):
            final_attr['target'] = tag['target']

    def handle_meta(self, tag, final_attr):
        if (tag.attrs.get('name', None) != 'homepage' or
                tag.attrs.get('value', None) != 'true'):
            return False
        final_attr['name'] = 'homepage'
        final_attr['value'] = 'true'

    def handle_img(self, tag, final_attr):
        if not tag.has_attr('src'):
            return False
        self.must_handle(tag['src'])
        for a in ['width', 'height', 'src', 'alt']:
            if tag.has_attr(a):
                final_attr[a] = tag[a]

    def handle_td(self, tag, final_attr):
        if tag.has_attr('rowspan'):
            final_attr['rowspan'] = tag['rowspan']
        if tag.has_attr('colspan'):
            final_attr['colspan'] = tag['colspan']

    def handle_default(self, tag, final_attr):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.dom.close()


if __name__ == '__main__':
    import urllib2
    res = urllib2.urlopen('https://xadmin.readthedocs.org'
                          '/en/latest/quickstart.html')
    import time
    now = time.time()
    parser = RawHtmlParser(lambda t: t)
    parser.feed(res.read())
    print "used time: ", time.time() - now
    print parser.read()
