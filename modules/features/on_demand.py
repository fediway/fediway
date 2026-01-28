def on_demand_feature_view(
    *,
    name: Optional[str] = None,
    entities: Optional[List[Entity]] = None,
    schema: list[Field],
    sources: list[
        Union[
            FeatureView,
            RequestSource,
            FeatureViewProjection,
        ]
    ],
    mode: str = "pandas",
    description: str = "",
    tags: Optional[dict[str, str]] = None,
    owner: str = "",
    write_to_online_store: bool = False,
    singleton: bool = False,
    explode: bool = False,
):
    """
    Creates an OnDemandFeatureView object with the given user function as udf.

    Args:
        name (optional): The name of the on demand feature view. If not provided, the name will be the name of the user function.
        entities (Optional): The list of names of entities that this feature view is associated with.
        schema: The list of features in the output of the on demand feature view, after
            the transformation has been applied.
        sources: A map from input source names to the actual input sources, which may be
            feature views, or request data sources. These sources serve as inputs to the udf,
            which will refer to them by name.
        mode: The mode of execution (e.g,. Pandas or Python Native)
        description (optional): A human-readable description.
        tags (optional): A dictionary of key-value pairs to store arbitrary metadata.
        owner (optional): The owner of the on demand feature view, typically the email
            of the primary maintainer.
        write_to_online_store (optional): A boolean that indicates whether to write the on demand feature view to
            the online store for faster retrieval.
        singleton (optional): A boolean that indicates whether the transformation is executed on a singleton
            (only applicable when mode="python").
        explode (optional): A boolean that indicates whether the transformation explodes the input data into multiple rows.
    """

    def mainify(obj) -> None:
        # Needed to allow dill to properly serialize the udf. Otherwise, clients will need to have a file with the same
        # name as the original file defining the ODFV.
        if obj.__module__ != "__main__":
            obj.__module__ = "__main__"

    def decorator(user_function):
        udf_string = dill.source.getsource(user_function)
        mainify(user_function)

        on_demand_feature_view_obj = OnDemandFeatureView(
            name=name if name is not None else user_function.__name__,
            sources=sources,
            schema=schema,
            mode=mode,
            description=description,
            tags=tags,
            owner=owner,
            write_to_online_store=write_to_online_store,
            entities=entities,
            singleton=singleton,
            udf=user_function,
            udf_string=udf_string,
        )
        functools.update_wrapper(wrapper=on_demand_feature_view_obj, wrapped=user_function)
        return on_demand_feature_view_obj

    return decorator
