def get_scaler(scaler: str):
    if scaler == "standard":
        from sklearn.preprocessing import StandardScaler

        return StandardScaler()

    raise NotImplementedError
