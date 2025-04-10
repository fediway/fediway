

def id_partition(instance_id: int) -> str:
    """
    Mimics Paperclip's partitioning of the id.
    Pads the id to 9 digits and splits into three parts.
    For example, 123 becomes "000/000/123".
    """

    padded = f"{instance_id:09d}"
    return f"{padded[0:3]}/{padded[3:6]}/{padded[6:9]}"