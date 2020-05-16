class AbstractMapper:
    def get_table_name(self) -> str:
        return 'tmp_table_name'

    def get_pk_column(self) -> str:
        return 'id'


class DataclassMapper(AbstractMapper):
    pass
