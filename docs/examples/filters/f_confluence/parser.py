from bs4 import BeautifulSoup, CData

__author__ = 'jay'


class ConfluencePageInflater(object):
    def __init__(self, page_source, page_handle, attach_handle,
                 encoding='utf-8'):
        super(ConfluencePageInflater, self).__init__()
        self.soup = BeautifulSoup(page_source, 'html5lib',
                                  from_encoding=encoding)
        self.page_handle = page_handle
        self.attach_handle = attach_handle
        self.cleaned_up = False

    def filter_image(self):
        for img in self.soup.find_all('img'):
            ac_image = self.soup.new_tag('ac:image')
            src = img.get('src')
            if src and '//' not in src:
                attach = self.attach_handle(src, img.get('title'))
                if attach:
                    ri_resource = self.soup.new_tag('ri:attachment')
                    ri_resource['ri:filename'] = attach['resource_name']
                else:
                    img.decompose()
                    continue
            else:
                ri_resource = self.soup.new_tag('ri:url')
                ri_resource['ri:value'] = src
            ac_image.append(ri_resource)
            if img.has_attr('alt'):
                ac_image['ac:alt'] = img['alt']
            img.replace_with(ac_image)

    def filter_link(self):
        for link in self.soup.find_all('a'):
            href = link.get('href')
            if href and '//' not in href:
                if '?' in href:
                    href = href[:href.index('?')]
                ac_link = self.soup.new_tag('ac:link')
                if '#' in href:
                    ac_link['ac:anchor'] = href[href.index('#') + 1:]
                    href = href[:href.index('#')]
                if href.endswith('.html'):
                    page = self.page_handle(href)
                    if page:
                        ri_resource = self.soup.new_tag('ri:page')
                        ri_resource['ri:content-title'] = page['title']
                    else:
                        link.decompose()
                        continue
                else:
                    attach = self.attach_handle(href, link.get('title'))
                    if attach:
                        ri_resource = self.soup.new_tag('ri:attachment')
                        ri_resource['ri:filename'] = attach['resource_name']
                    else:
                        link.decompose()
                        continue
                ac_link.append(ri_resource)
                children = link.find_all()
                if children:
                    body = self.soup.new_tag('ac:link-body')
                    for child in children:
                        body.append(child)
                elif link.text:
                    body = self.soup.new_tag('ac:plain-text-link-body')
                    body.append(self.soup.new_string(link.text, CData))
                else:
                    link.decompose()
                    continue
                if link.has_attr('title'):
                    ac_link['ac:title'] = link['title']
                ac_link.append(body)
                link.replaceWith(ac_link)

    @property
    def title(self):
        title = self.soup.find('title')
        return title and title.encode_contents().strip() or ''

    def filter_dl(self):
        for dl in self.soup.find_all('dl'):
            ul = self.soup.new_tag('ul')
            dts = dl.find_all('dt')
            dds = dl.find_all('dd')
            for dt, dd in zip(dts, dds):
                li = self.soup.new_tag('li')
                dt.name = 'p'
                li.append(dt)
                dd.name = 'p'
                li.append(dd)
                ul.append(li)
            dl.replace_with(ul)

    @property
    def is_home_page(self):
        meta = self.soup.find('meta', attrs={'name': 'homepage'})
        return meta is not None and meta.get('value') == 'true'

    def filter_code(self):
        for pre in self.soup.find_all('pre'):
            code_block = self.soup.new_tag('ac:structured-macro')
            code_block['ac:name'] = 'code'

            if pre.has_attr('data-lang'):
                lang_param = self.soup.new_tag('ac:parameter')
                lang_param['ac:name'] = 'language'
                lang_param.append(pre['data-lang'])
                code_block.append(lang_param)

            plain_text = self.soup.new_tag('ac:plain-text-body')
            plain_text.append(self.soup.new_string(pre.get_text(), CData))
            code_block.append(plain_text)
            pre.replace_with(code_block)

    @property
    def cleaned_src(self):
        if not self.cleaned_up:
            self.cleaned_up = True
            self.filter_image()
            self.filter_link()
            self.filter_dl()
            self.filter_code()
        body = self.soup.find('body')
        return (body and body.encode_contents(formatter='html') or
                self.soup.encode_contents(formatter='html'))

if __name__ == '__main__':
    def get_resource_by_href(href, *args):
        return {'resource_name': href, 'title': href}
    import requests
    import contextlib
    inflater = ConfluencePageInflater("<dl><dt><strong>hi</strong></dt><dd>tdse</dd></dl>",
                                      get_resource_by_href,
                                      get_resource_by_href)
    print inflater.cleaned_src
    print inflater.title
    print inflater.is_home_page
    with contextlib.closing(requests.get('http://www.redhat.com')) as res:
        inflater = ConfluencePageInflater(res.content,
                                          get_resource_by_href,
                                          get_resource_by_href)
        print inflater.cleaned_src
        print inflater.title
        print inflater.is_home_page
