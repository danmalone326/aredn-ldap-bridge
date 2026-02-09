from __future__ import annotations

from typing import Tuple

from pyasn1.codec.ber import decoder, encoder
from pyasn1.error import SubstrateUnderrunError
from pyasn1.type import namedtype, namedval, tag, univ


class LDAPString(univ.OctetString):
    pass


class LDAPDN(LDAPString):
    pass


class MessageID(univ.Integer):
    pass


class ResultCode(univ.Enumerated):
    namedValues = namedval.NamedValues(
        ("success", 0),
        ("operationsError", 1),
        ("protocolError", 2),
        ("timeLimitExceeded", 3),
        ("sizeLimitExceeded", 4),
        ("compareFalse", 5),
        ("compareTrue", 6),
        ("authMethodNotSupported", 7),
        ("strongerAuthRequired", 8),
        ("noSuchAttribute", 16),
        ("undefinedAttributeType", 17),
        ("inappropriateMatching", 18),
        ("constraintViolation", 19),
        ("attributeOrValueExists", 20),
        ("invalidAttributeSyntax", 21),
        ("noSuchObject", 32),
        ("aliasProblem", 33),
        ("invalidDNSyntax", 34),
        ("aliasDereferencingProblem", 36),
        ("inappropriateAuthentication", 48),
        ("invalidCredentials", 49),
        ("insufficientAccessRights", 50),
        ("busy", 51),
        ("unavailable", 52),
        ("unwillingToPerform", 53),
        ("loopDetect", 54),
        ("namingViolation", 64),
        ("objectClassViolation", 65),
        ("notAllowedOnNonLeaf", 66),
        ("notAllowedOnRDN", 67),
        ("entryAlreadyExists", 68),
        ("objectClassModsProhibited", 69),
        ("other", 80),
    )


class AttributeDescription(LDAPString):
    pass


class AssertionValue(univ.OctetString):
    pass


class AttributeValueAssertion(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType("attributeDesc", AttributeDescription()),
        namedtype.NamedType("assertionValue", AssertionValue()),
    )


class Substring(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType(
            "initial",
            AssertionValue().subtype(
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)
            ),
        ),
        namedtype.NamedType(
            "any",
            AssertionValue().subtype(
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)
            ),
        ),
        namedtype.NamedType(
            "final",
            AssertionValue().subtype(
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)
            ),
        ),
    )


class Substrings(univ.SequenceOf):
    componentType = Substring()


class SubstringFilter(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType("type", AttributeDescription()),
        namedtype.NamedType("substrings", Substrings()),
    )


class MatchingRuleId(LDAPString):
    pass


class AttributeType(LDAPString):
    pass


class MatchingRuleAssertion(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType(
            "matchingRule",
            MatchingRuleId().subtype(
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)
            ),
        ),
        namedtype.OptionalNamedType(
            "type",
            AttributeType().subtype(
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)
            ),
        ),
        namedtype.OptionalNamedType(
            "matchValue",
            AssertionValue().subtype(
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)
            ),
        ),
        namedtype.OptionalNamedType(
            "dnAttributes",
            univ.Boolean().subtype(
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4)
            ),
        ),
    )


class Filter(univ.Choice):
    pass


class FilterSet(univ.SequenceOf):
    componentType = Filter()


Filter.componentType = namedtype.NamedTypes(
    namedtype.NamedType(
        "and_",
        FilterSet().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)
        ),
    ),
    namedtype.NamedType(
        "or_",
        FilterSet().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)
        ),
    ),
    namedtype.NamedType(
        "not_",
        Filter().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2)
        ),
    ),
    namedtype.NamedType(
        "equalityMatch",
        AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 3)
        ),
    ),
    namedtype.NamedType(
        "substrings",
        SubstringFilter().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4)
        ),
    ),
    namedtype.NamedType(
        "greaterOrEqual",
        AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5)
        ),
    ),
    namedtype.NamedType(
        "lessOrEqual",
        AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 6)
        ),
    ),
    namedtype.NamedType(
        "present",
        AttributeDescription().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 7)
        ),
    ),
    namedtype.NamedType(
        "approxMatch",
        AttributeValueAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 8)
        ),
    ),
    namedtype.NamedType(
        "extensibleMatch",
        MatchingRuleAssertion().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 9)
        ),
    ),
)

# Ensure FilterSet uses the fully-defined Filter type.
FilterSet.componentType = Filter()


class AttributeSelection(univ.SequenceOf):
    componentType = AttributeDescription()


class BindRequest(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType("version", univ.Integer()),
        namedtype.NamedType("name", LDAPDN()),
        namedtype.NamedType(
            "authentication",
            univ.Choice(
                componentType=namedtype.NamedTypes(
                    namedtype.NamedType(
                        "simple",
                        univ.OctetString().subtype(
                            implicitTag=tag.Tag(
                                tag.tagClassContext, tag.tagFormatSimple, 0
                            )
                        ),
                    )
                )
            ),
        ),
    )


class BindRequestMessage(BindRequest):
    tagSet = BindRequest.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 0)
    )


class BindResponse(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType("resultCode", ResultCode()),
        namedtype.NamedType("matchedDN", LDAPDN()),
        namedtype.NamedType("diagnosticMessage", LDAPString()),
    )


class BindResponseMessage(BindResponse):
    tagSet = BindResponse.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 1)
    )


class SearchRequest(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType("baseObject", LDAPDN()),
        namedtype.NamedType(
            "scope",
            univ.Enumerated(
                namedValues=namedval.NamedValues(
                    ("baseObject", 0),
                    ("singleLevel", 1),
                    ("wholeSubtree", 2),
                )
            ),
        ),
        namedtype.NamedType(
            "derefAliases",
            univ.Enumerated(
                namedValues=namedval.NamedValues(
                    ("neverDerefAliases", 0),
                    ("derefInSearching", 1),
                    ("derefFindingBaseObj", 2),
                    ("derefAlways", 3),
                )
            ),
        ),
        namedtype.NamedType("sizeLimit", univ.Integer()),
        namedtype.NamedType("timeLimit", univ.Integer()),
        namedtype.NamedType("typesOnly", univ.Boolean()),
        namedtype.NamedType("filter", Filter()),
        namedtype.NamedType("attributes", AttributeSelection()),
    )


class SearchRequestMessage(SearchRequest):
    tagSet = SearchRequest.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 3)
    )


class AttributeValue(univ.OctetString):
    pass


class PartialAttribute(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType("type", AttributeDescription()),
        namedtype.NamedType("vals", univ.SetOf(componentType=AttributeValue())),
    )


class PartialAttributeList(univ.SequenceOf):
    componentType = PartialAttribute()


class SearchResultEntry(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType("objectName", LDAPDN()),
        namedtype.NamedType("attributes", PartialAttributeList()),
    )


class SearchResultEntryMessage(SearchResultEntry):
    tagSet = SearchResultEntry.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 4)
    )


class SearchResultDone(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType("resultCode", ResultCode()),
        namedtype.NamedType("matchedDN", LDAPDN()),
        namedtype.NamedType("diagnosticMessage", LDAPString()),
    )


class SearchResultDoneMessage(SearchResultDone):
    tagSet = SearchResultDone.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 5)
    )


class ProtocolOp(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType("bindRequest", BindRequestMessage()),
        namedtype.NamedType("bindResponse", BindResponseMessage()),
        namedtype.NamedType("searchRequest", SearchRequestMessage()),
        namedtype.NamedType("searchResEntry", SearchResultEntryMessage()),
        namedtype.NamedType("searchResDone", SearchResultDoneMessage()),
        namedtype.NamedType("unbindRequest", univ.Null().subtype(
            implicitTag=tag.Tag(tag.tagClassApplication, tag.tagFormatSimple, 2)
        )),
    )


class LDAPMessage(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType("messageID", MessageID()),
        namedtype.NamedType("protocolOp", ProtocolOp()),
    )


class SearchRequestLoose(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType("baseObject", LDAPDN()),
        namedtype.NamedType(
            "scope",
            univ.Enumerated(
                namedValues=namedval.NamedValues(
                    ("baseObject", 0),
                    ("singleLevel", 1),
                    ("wholeSubtree", 2),
                )
            ),
        ),
        namedtype.NamedType(
            "derefAliases",
            univ.Enumerated(
                namedValues=namedval.NamedValues(
                    ("neverDerefAliases", 0),
                    ("derefInSearching", 1),
                    ("derefFindingBaseObj", 2),
                    ("derefAlways", 3),
                )
            ),
        ),
        namedtype.NamedType("sizeLimit", univ.Integer()),
        namedtype.NamedType("timeLimit", univ.Integer()),
        namedtype.NamedType("typesOnly", univ.Boolean()),
        namedtype.NamedType("filter", univ.Any()),
        namedtype.NamedType("attributes", AttributeSelection()),
    )


class SearchRequestLooseMessage(SearchRequestLoose):
    tagSet = SearchRequestLoose.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 3)
    )


class ProtocolOpLoose(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType("bindRequest", BindRequestMessage()),
        namedtype.NamedType("bindResponse", BindResponseMessage()),
        namedtype.NamedType("searchRequest", SearchRequestLooseMessage()),
        namedtype.NamedType("searchResEntry", SearchResultEntryMessage()),
        namedtype.NamedType("searchResDone", SearchResultDoneMessage()),
        namedtype.NamedType("unbindRequest", univ.Null().subtype(
            implicitTag=tag.Tag(tag.tagClassApplication, tag.tagFormatSimple, 2)
        )),
    )


class LDAPMessageLoose(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType("messageID", MessageID()),
        namedtype.NamedType("protocolOp", ProtocolOpLoose()),
    )


def decode_ldap_message(data: bytes):
    return decoder.decode(data, asn1Spec=LDAPMessageLoose())


def peek_ldap_op_tag(data: bytes) -> str:
    if len(data) < 2:
        return "unknown"
    _, length_len = _ber_length_len(data, 1)
    start = 1 + length_len
    if start >= len(data):
        return "unknown"
    tag_byte = data[start]
    tag_class = (tag_byte & 0xC0) >> 6
    tag_form = (tag_byte & 0x20) >> 5
    tag_number = tag_byte & 0x1F
    return f"{tag_class}:{tag_form}:{tag_number}"


def _ber_length_len(data: bytes, offset: int) -> tuple[int, int]:
    if offset >= len(data):
        return 0, 0
    first = data[offset]
    if first & 0x80 == 0:
        return first, 1
    num_len_bytes = first & 0x7F
    return 0, 1 + num_len_bytes


def encode_ldap_message(message: LDAPMessage) -> bytes:
    return encoder.encode(message)


def make_ldap_message(message_id: int, op_name: str, op_value: univ.Asn1Item) -> LDAPMessage:
    protocol_op = ProtocolOp()
    protocol_op.setComponentByName(op_name, op_value)
    message = LDAPMessage()
    message.setComponentByName("messageID", message_id)
    message.setComponentByName("protocolOp", protocol_op)
    return message


def build_bind_response(message_id: int, result_code: int = 0) -> LDAPMessage:
    response = BindResponseMessage()
    response.setComponentByName("resultCode", result_code)
    response.setComponentByName("matchedDN", b"")
    response.setComponentByName("diagnosticMessage", b"")
    return make_ldap_message(message_id, "bindResponse", response)


def build_search_result_entry(
    message_id: int,
    dn: str,
    attributes: list[tuple[str, list[str]]],
) -> LDAPMessage:
    entry = SearchResultEntryMessage()
    entry.setComponentByName("objectName", dn)

    attr_list = PartialAttributeList()
    for attr_name, attr_vals in attributes:
        partial = PartialAttribute()
        partial.setComponentByName("type", attr_name)
        values = univ.SetOf(componentType=AttributeValue())
        for val in attr_vals:
            values.append(AttributeValue(val.encode("utf-8")))
        partial.setComponentByName("vals", values)
        attr_list.append(partial)

    entry.setComponentByName("attributes", attr_list)
    return make_ldap_message(message_id, "searchResEntry", entry)


def build_search_result_done(message_id: int, result_code: int = 0) -> LDAPMessage:
    done = SearchResultDoneMessage()
    done.setComponentByName("resultCode", result_code)
    done.setComponentByName("matchedDN", b"")
    done.setComponentByName("diagnosticMessage", b"")
    return make_ldap_message(message_id, "searchResDone", done)
