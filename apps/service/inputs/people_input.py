import graphene


class PeopleModifiedAfterFilterInput(graphene.InputObjectType):
    """Input to fetch people details based on modification timestamp and business unit."""
    mdtz=graphene.String(required=True,description="Modification timestamp")
    ctzoffset=graphene.Int(required=True,description="Client timezone offset")
    buid=graphene.Int(required=True,description="Business unit id")


class PeopleEventLogPunchInsFilterInput(graphene.InputObjectType):
    """Input to fetch people event log punch ins details based on date for, business unit and people id."""
    datefor=graphene.String(required=True,description="Date for")
    buid=graphene.Int(required=True,description="Business unit id")
    peopleid=graphene.Int(required=True,description="People id")


class PgbelongingModifiedAfterFilterInput(graphene.InputObjectType):
    """Input to fetch people belonging details based on modification timestamp, business unit and people id."""
    mdtz=graphene.String(required=True,description="Modification timestamp")
    ctzoffset=graphene.Int(required=True,description="Client timezone offset")
    buid=graphene.Int(required=True,description="Business unit id")
    peopleid=graphene.Int(required=True,description="People id")

class PeopleEventLogHistoryFilterInput(graphene.InputObjectType):
    """Input to fetch people event log history details based on modification timestamp, business unit, client id, people id and pevent type id."""
    mdtz=graphene.String(required=True,description="Modification timestamp")
    ctzoffset=graphene.Int(required=True,description="Client timezone offset")
    peopleid=graphene.Int(required=True,description="People id")
    buid=graphene.Int(required=True,description="Business unit id")
    clientid=graphene.Int(required=True,description="Client id")
    peventtypeid=graphene.Int(required=True,description="Pevent type id")

class AttachmentFilterInput(graphene.InputObjectType):
    """Input to fetch attachment details based on owner."""
    owner=graphene.String(required=True,description="Owner")


