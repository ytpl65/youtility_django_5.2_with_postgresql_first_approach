import graphene


class AssetFilterInput(graphene.InputObjectType):
    """Input to fetch asset details based on modification timestamp and business unit."""
    mdtz = graphene.String(required = True,description="Modification timestamp")
    ctzoffset = graphene.Int(required = True,description="Client timezone offset")
    buid = graphene.Int(required = True,description="Business unit id")

    