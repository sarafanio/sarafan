import re
import logging
from dataclasses import make_dataclass, field, fields, dataclass
from typing import Dict, List, Type, Union, Optional

from Cryptodome.Hash import keccak
from eth_abi import decode_abi, decode_single, encode_abi, encode_single
from .event import Event

log = logging.getLogger(__name__)


ETH_TO_DATACLASS_TYPE = {
    "uint256": int,
    "uint32": int,
    "bytes32": bytes,
    "address": str,
}


camel_case_pattern = re.compile(r"(?<!^)(?=[A-Z])")


def camel_to_snake(value):
    """Convert camel case string to snake case.

    Used to convert contract methodName to pythonistic method_name.
    """
    return camel_case_pattern.sub("_", value).lower()


def abi_to_signature(abi: Dict) -> bytes:
    """Get first 4 bytes of signature hash for provided method definition.

    Used to build method call transaction.
    """
    input_types = ",".join([i["type"] for i in abi["inputs"]])
    signature = "{}({})".format(abi["name"], input_types)
    return keccak.new(digest_bytes=32, data=bytes(signature, "ascii")).digest()[:4]


@dataclass
class BaseContractEvent:
    """Base class for contract events.

    Extends base event with contract-specific fields parsed from topics and data.

    Contains `from_event` method to parse event data to contract-specific event.
    """

    def __init__(self, *args, **kwargs):  # for linter
        super().__init__(*args, **kwargs)  # pragma: no cover

    def data(self):
        """Get encoded data for contract event.
        """
        input_types = []
        input_values = []
        for f in fields(self):
            if not f.metadata["abi_indexed"]:
                input_types.append(f.metadata["abi_type"])
                value = getattr(self, f.name)
                # if ETH_TO_DATACLASS_TYPE[f.metadata["abi_type"]] is str:
                #     value = bytes(value, 'ascii')
                input_values.append(value)
        return '0x' + encode_abi(input_types, input_values).hex()

    def topics(self):
        """Get encoded topics list for contract event.
        """
        return ['0x%s' % self.get_signature_hash()] + [
            '0x' + encode_single(f.metadata["abi_type"], getattr(self, f.name)).hex()
            for f in fields(self) if f.metadata["abi_indexed"]
        ]

    def topics_types(self) -> Dict:
        indexed_types = []
        indexed_names = []
        for f in fields(self):
            if f.metadata["abi_indexed"]:
                indexed_types.append(f.metadata["abi_type"])
                indexed_names.append(f.name)
        return dict(zip(indexed_names, indexed_types))

    @classmethod
    def from_event(cls, event: Event):
        """Decode event data to contract event.
        """
        # collect information about `data` fields positions and types,
        # and indexed field types (in topics)
        # TODO: we should do it only once
        input_types = []
        field_names = []
        indexed_types = []
        indexed_names = []
        for f in fields(cls):
            if f.metadata["abi_indexed"]:
                indexed_types.append(f.metadata["abi_type"])
                indexed_names.append(f.name)
            else:
                input_types.append(f.metadata["abi_type"])
                field_names.append(f.name)

        # decode `topics` using collected type information and merge them with
        # names by position
        data = {
            n: decode_single(t, bytes.fromhex(d[2:]))
            for n, t, d in zip(indexed_names, indexed_types, event.topics[1:])
        }
        # decode events `data` content using collected indexed types
        decoded = decode_abi(input_types, bytes.fromhex(event.data[2:]))
        # merge decoded values with field name by position and update
        data.update(dict(zip(field_names, decoded)))
        # convert camel-case event property names to snake-case
        snake_data = {camel_to_snake(key): value for key, value in data.items()}
        # apply fields transformations
        for f in fields(cls):
            if f.metadata.get("abi_hex_bytes"):
                snake_data[f.name] = snake_data[f.name].hex()
            elif f.metadata.get("abi_ascii_bytes"):
                snake_data[f.name] = snake_data[f.name].decode('ascii')
        return cls(**snake_data)

    @classmethod
    def get_signature_hash(cls):
        """Get event signature hash.
        """
        args_sig = ",".join([f.metadata["abi_type"] for f in fields(cls)])
        return keccak.new(
            digest_bytes=32, data=bytes(f"{cls.__name__}({args_sig})", "ascii")
        ).hexdigest()


class ContractMethod:
    """Contract method callable.

    Instance should be instantiated with at minimum single abi definition.

    There are could be multiple method signatures. Additional signatures can be added
    with `extend_signature()`.

    Can be used to build transactions with method invocation.
    """

    abi_list: List[Dict]

    def __init__(self, abi: Union[Dict, List]):
        self.abi_list = []
        if isinstance(abi, Dict):
            self.extend_signature(abi)
        elif isinstance(abi, List):
            self.name = abi[0]["name"]
            for item in abi:
                if item["name"] != self.name:
                    raise ValueError(
                        "Different names for the same method %s "
                        "(%s expected)" % (item["name"], self.name)
                    )
                self.extend_signature(item)
        else:
            raise TypeError("`abi` should be a definition or list of definitions")

    def extend_signature(self, abi: Dict):
        """Extend method signature with additional definition.

        :param abi: abi method definition (`name` and `inputs` keys are required)
        """
        if "name" not in abi:
            log.error("Wrong abi definition %s", abi)
            raise TypeError("Invalid ABI method definition, name key required")
        if "inputs" not in abi:
            log.error("No inputs key found in abi definition %s", abi)
            raise TypeError(
                "Invalid ABI method definition, no inputs "
                "(should be at least an empty list)"
            )
        self.abi_list.append(abi)

    def select_abi(self, *args, **kwargs):
        """Select abi definition matching arguments.
        """
        total_inputs = len(args) + len(kwargs)
        for abi in self.abi_list:
            inputs = list(abi["inputs"])
            if len(inputs) != total_inputs:
                continue
            inputs = inputs[len(args):]
            input_names = {i["name"] for i in inputs}
            for key in kwargs:
                input_names.remove(key)
            if not input_names:
                return abi
        raise RuntimeError("No matching signature")

    def __call__(self, *args, **kwargs):
        """Return transaction data with method invocation.
        """
        abi = self.select_abi(*args, **kwargs)
        data = abi_to_signature(abi)
        ordered_args = args + tuple(
            kwargs[i["name"]] for i in abi["inputs"][len(args):]
        )
        arguments = encode_abi([i["type"] for i in abi["inputs"]], ordered_args)
        data += arguments
        return data


class Contract:
    """Ethereum contract interface.

    The main purpose is to parse events basing on contract abi, see `parse()`.
    """

    #: contract address
    address: str
    #: map event name to event type class
    event_types: Dict[str, Type[BaseContractEvent]]
    #: contract method names mapped to method instance
    contract_methods: Dict[str, ContractMethod]
    #: mapping of abi method signature hash to event type
    signatures: Dict[str, Type[BaseContractEvent]]

    def __init__(self,
                 address: str,
                 abi: List,
                 event_classes: Optional[Dict[str, Type[BaseContractEvent]]] = None):
        self.event_types = {}
        self.signatures = {}
        self.address = address
        self.abi = abi
        self.contract_methods = {}
        self.event_types = event_classes or {}
        self._create_event_classes()

    def event(self, name) -> Type[BaseContractEvent]:
        """Get event class for event name.

        :param name: contract event name
        """
        return self.event_types[name]

    def parse(self, event: Event) -> BaseContractEvent:
        """Parse blockchain event and return contract specific event instance.
        """
        type_cls = self.signatures[event.topics[0][2:]]
        return type_cls.from_event(event)

    def call(self, method_name, *args, **kwargs) -> bytes:
        """Get transaction data for method call.
        """
        return self.contract_methods[method_name](*args, **kwargs)

    def _create_event_classes(self):
        """Create classes for contract events.
        """
        for item in self.abi:
            item_type = item.get("type")
            if item_type == "event":
                event_type = self.event_types.get(item.get('name'))
                if not event_type:
                    cls_fields = []
                    for input in item["inputs"]:
                        field_type = ETH_TO_DATACLASS_TYPE[input["type"]]
                        cls_field_name = camel_to_snake(input["name"])
                        # prepend python keywords with underscore
                        if cls_field_name in ("from",):
                            cls_field_name = "_%s" % cls_field_name
                        cls_fields.append(
                            (
                                cls_field_name,
                                field_type,
                                field(
                                    metadata={
                                        "abi_name": input["name"],
                                        "abi_indexed": input["indexed"],
                                        "abi_type": input["type"],
                                    }
                                ),
                            )
                        )
                    event_type = make_dataclass(
                        item["name"], cls_fields, bases=(BaseContractEvent,)
                    )
                self.event_types[item["name"]] = event_type
                setattr(self, item["name"], event_type)
                log.debug(
                    "Add signature for Event %s: %s",
                    event_type,
                    event_type.get_signature_hash(),
                )
                self.signatures[event_type.get_signature_hash()] = event_type
            elif item_type == "function":
                if item["name"] in self.contract_methods:
                    self.contract_methods[item["name"]].extend_signature(item)
                else:
                    self.contract_methods[item["name"]] = ContractMethod(item)
                    setattr(self, item["name"], ContractMethod(item))
