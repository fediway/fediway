from sqlmodel import SQLModel

def has_changed(model: SQLModel, values: object):
    """
    Check if the values of a models are different to new values.
    """
    
    return not all(getattr(model, key) == values[key] for key in values.keys())

