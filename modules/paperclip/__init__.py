

def id_partition(instance_id: int) -> str:
    """
    Mimics Paperclip's partitioning of the id.
    Pads the id to digits and splits into three parts.
    E.g.: "000/000/123".
    """

    id_str = str(instance_id)
    return "/".join([id_str[i:i+3] for i in range(0, 18, 3)])