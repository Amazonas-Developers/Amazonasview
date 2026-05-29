from PIL import Image



def buffer_to_png(bmpstr, width=None, height=None, output_path="output.png"):
    """
    Convierte un buffer BGRX en PNG.
    Si no se pasan width/height, intenta deducirlos.
    """
    bytes_per_pixel = 4
    total_pixels = len(bmpstr) // bytes_per_pixel

    if width is None and height is None:
        raise ValueError('Debes especificar al menos width o height para deducir la otra dimensión')

    if width is None:
        width = total_pixels // height
    if height is None:
        height = total_pixels // width

    im = Image.frombuffer(
        'RGB',
        (width, height),
        bmpstr,
        'raw',
        'BGRX',
        0,
        1
    )
    im.save(output_path, format='PNG')
    return output_path