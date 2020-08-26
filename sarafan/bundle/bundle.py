import json
from dataclasses import dataclass
from typing import Optional, IO, Union, Dict
from zipfile import ZipFile


class BundleError(Exception):
    pass


class BundleFormatError(BundleError):
    pass


class UnsupportedBundleVersion(BundleFormatError):
    pass


class UnsafeBundleContent(BundleError):
    pass


@dataclass
class ContentJSON:
    """Bundles content.json representation.

    Has `parse` method to create object from different sources (fp, str, dict).
    """
    version: str = '1.0'
    index: Optional[str] = None
    text: Optional[str] = None
    nonce: Optional[str] = None

    @classmethod
    def parse(cls, content: Union[str, IO, Dict]) -> 'ContentJSON':
        """Create ContentJSON from string, file-like object or dict.
        """
        try:
            if isinstance(content, IO):
                content = json.load(content)
            elif isinstance(content, str):
                content = json.loads(content)
            elif not isinstance(content, Dict):
                raise TypeError("Can't parse content.json: unsupported content type "
                                "%s." % type(content))
        except (json.JSONDecodeError, IOError) as e:
            raise BundleFormatError from e

        try:
            return cls(**content)
        except TypeError as e:
            raise BundleFormatError from e

    def __post_init__(self):
        version = self.version
        if version != '1.0':
            raise UnsupportedBundleVersion("Unsupported bundle version %s" % version)

        if not any([self.index, self.text]):
            raise BundleFormatError("The `index` file or `text` should be specified "
                                    "in content.json")


class ContentBundle(ZipFile):
    """Sarafan content bundle.

    Allows to read and write sarafan archives. It is based on ZipFile and adds
    some helper methods.
    """
    text_extensions = ['.md', '.txt']
    text_index_names = {f'index{x}' for x in text_extensions}

    image_extensions = ['.png', '.jpg', '.gif', '.vgif']
    image_index_names = {f'index{x}' for x in image_extensions}

    allowed_extensions = text_extensions + image_extensions

    def render_markdown(self):
        """Convert bundle to markdown according to content type.

        :return: markdown text
        """
        bundle_names = set(self.namelist())
        if 'content.json' in bundle_names:
            # apply content.json rules
            return self._render_content_json()
        elif bundle_names.intersection(self.text_index_names):
            # use text as source
            # choose one of the index files in the right order
            for name in self.text_index_names:
                if name in bundle_names:
                    text_content = self.read(name)
                    return self._render_text(text_content)
        elif bundle_names.intersection(self.image_index_names):
            # build text content from image
            # choose one of the index files in the right order
            for name in self.image_index_names:
                if name in bundle_names:
                    return self._render_image(name)

    def extractall(self, path=None, members=None, pwd=None, strict=False):
        """Extract all members from the archive to the current working
           directory. `path' specifies a different directory to extract to.
           `members' is optional and must be a subset of the list returned
           by namelist().
        """
        allowed_members = []
        if members is None:
            members = self.namelist()
        for name in members:
            ext = name.split('.')[-1]
            if ext in self.allowed_extensions:
                allowed_members.append(name)
            elif strict:
                raise UnsafeBundleContent(name)
        super().extractall(path=path, members=allowed_members, pwd=pwd)

    def _render_content_json(self):
        """Render bundle content to markdown using content.json parameters.

        :return:
        """
        content_json = ContentJSON.parse(self.read('content.json').decode())
        if content_json.index:
            try:
                ext = content_json.index.split('.')[-1]
            except IndexError:
                raise BundleFormatError("Index file %s in content.json has no extension"
                                        % content_json.index)
            if ext in self.text_extensions:
                return self._render_text(self.read(content_json.index))
            elif ext in self.image_extensions:
                return self._render_image(content_json.index, content_json.text)
            else:
                raise BundleFormatError("Unsupported index file %s extension" % content_json.index)
        return self._render_text(content_json.text)

    def _render_text(self, text_content: str):
        """Render text content and apply custom transformations.
        """
        return text_content

    def _render_image(self, image_uri: str, text_content: Optional[str] = None):
        """Render content to markdown from image and optional text.
        """
        content = f"![image]({image_uri})"
        if text_content:
            content = '\n\n'.join([
                content,
                self._render_text(text_content)
            ])
        return content
