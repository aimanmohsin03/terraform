from adapters.dummydb_adapter import DummyDbAdapter
from adapters.ubuntu_pg_adapter import UbuntuPgAdapter
from adapters.rocksdb_adapter import RocksDbAdapter


class AdapterFactory:
    @staticmethod
    def get_adapter(adapter_data=None):
        if adapter_data is None:
            raise ValueError("adapter_data missing")
        if "DBMS" not in adapter_data:
            raise ValueError("DBMS missing in adapter_data")
        if adapter_data["DBMS"] == "PostgreSQL":
            return UbuntuPgAdapter(adapter_data)
        if adapter_data["DBMS"] == "RocksDB":
            return RocksDbAdapter(adapter_data)
        if adapter_data["DBMS"] == "DummyDB":
            return DummyDbAdapter(adapter_data)
        raise ValueError("DBMS {} not supported".format(adapter_data["DBMS"]))
