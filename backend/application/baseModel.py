# from application import db
from application.DBModels import db



class BaseModel(db.Model):
    __abstract__ = True

    #  Not working
    # def dump(self) -> str:
    #     if not hasattr(self.__class__, '__dumpFn'):
    #         def makeDumpFn(schema):  # Factory function that generates a "condition setter" for "option"
    #             def dumpFn(self):
    #                 associatedSchema = [schemaClass for schemaClass in base_registry if schemaClass.Meta.model is self.__class__]
    #                 if len(associatedSchema) == 1:
    #                     associatedSchema = associatedSchema[0]
    #                 else:
    #                     raise Exception('Could not find associated schema')
    #                 associatedSchema().dump(self)
    #             return dumpFn
    #         setattr(self.__class__, '__dumpFn', makeDumpFn)
    #     return self.__class__.__dumpFn(self)


    def __repr__(self):
        return "<{self.__class__.__name__}>(id={self.id!r})".format(self=self)

