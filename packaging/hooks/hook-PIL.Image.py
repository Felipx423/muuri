# The desktop app reads GIF/PNG/ICO assets; no document or AVIF codecs are used.
hiddenimports = [
    'PIL.BmpImagePlugin', 'PIL.GifImagePlugin', 'PIL.IcoImagePlugin',
    'PIL.PngImagePlugin', 'PIL.JpegImagePlugin',
]
