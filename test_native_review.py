"""
Regression tests for the native speaker corrections, Spanish (2026-10-01), Arabic
(2026-10-04), Portuguese (2026-10-08, integrated 2026-10-12) and French (register,
integrated 2026-10-14) and Lithuanian (11 of 15 returned corrections, integrated
2026-10-14, 4 held) and Bulgarian (14 of 16 corrections, integrated 2026-10-14, 2
held), and for every unflagged or held row in those six languages. A
digest of every language's text guards all 73 languages against unintended edits.

Each row is pinned by the SHA-256 of its template and of its rendered bank text.
The 27 corrected rows were pinned from the corrections themselves (the review
follow-through for Spanish and Arabic, the reviewer's sheet for Portuguese), NOT read
back from the generator, so a regression in the generator
fails here instead of being copied into the expectation. The 36 unflagged rows are
pinned as they stood on 2026-10-12, so an accidental edit to a row nobody reviewed
also fails. Hashes, not text, so the attack strings are not duplicated in the repo.

An intended change to any of these rows (for example a new round of native
feedback) must update the pin here AND append a deviation to PREREGISTRATION.md.

Run: python test_native_review.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from generate_attack_bank import CANARY, CATEGORIES, CONTROL, TEXT  # noqa: E402

BANK = json.loads((ROOT / "attack_bank.json").read_text(encoding="utf-8"))
CASES: list[tuple[str, bool]] = []


def check(name: str, ok) -> None:
    CASES.append((name, bool(ok)))


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# id -> (template sha256, rendered bank text sha256, corrected by a native speaker)
PINS = {
    "es_instruction_override_0": ("fd03c542feb51abcd2e6657fba5167d6f305d800fa9fb6128faeb28321f9fea7",
                                  "cd48d9cfcd61d428da5270b287632f4f1041b7bee7d5b6b98386dc5c9c121801", False),
    "es_instruction_override_1": ("45c317296fc11acf68aa92741ad4403a50f077343073e2e8ec59e0b1ab670b46",
                                  "7df36495bbe07982c9df5ba3affd13bd95b9c23329096bea76803b8648303f79", True),
    "es_instruction_override_2": ("367ef26c3d1ffdfc12915cd94ee25d31607eecf77403ab88c2dad3a9770d1b6e",
                                  "0da20f824177c73db9cf9bfb1648f5f7ceb820a861254294e7b71f9d5fc252f9", False),
    "es_role_play_jailbreak_0": ("1cbb7fc49c316b2485a07458e438c287f94858ee6c5ee48df520c74cfa33b5d2",
                                 "eefa2651a5fe34ce63341129b23ef709f3d776a237b26e6e4508a67a10ca6381", False),
    "es_role_play_jailbreak_1": ("e35766fd2e11b3be492cf21f27786e76a63cf41e73a231c01cbe4eee0ebdf858",
                                 "3747dddf2a212b6d6fb82ba9070a8cced1019dff7a999284ae5f64f30b7fbbf8", False),
    "es_role_play_jailbreak_2": ("3c8710dec291c0f8ea64966a8b79704e0dc9265705f2bdc6420b84950a983867",
                                 "224efcd6e75d9e8944eec0838951a396ebb590e67990e53f8136fd6b99a0a6a3", False),
    "es_system_prompt_extraction_0": ("1dda926ce338e185017f3dd2d1180b652fdaf1e2ba7014d2168815601040d010",
                                      "1dda926ce338e185017f3dd2d1180b652fdaf1e2ba7014d2168815601040d010", False),
    "es_system_prompt_extraction_1": ("7854b9104fa249d804d444badaa3a26ac3a81023196663e005d92ea3595267da",
                                      "7854b9104fa249d804d444badaa3a26ac3a81023196663e005d92ea3595267da", False),
    "es_system_prompt_extraction_2": ("8c87b89d31a232779efb265a53153713125158450d3160ab79bf0550e7eafb67",
                                      "8c87b89d31a232779efb265a53153713125158450d3160ab79bf0550e7eafb67", True),
    "es_obfuscated_payload_0": ("398c950345b9cf9539007c6e28b56690f0d2dce24a2b14a23db47fc2dd8b87be",
                                "d877c0e1031c83737d29d243e5136ffaf1218b77f4a818cf2ad577b311202aba", False),
    "es_obfuscated_payload_1": ("b51d9a59d83f2fda70e2b7169101ecfea03f505417ca941d4c6f348b0d64e443",
                                "8922502f1a3126a93235a457a6b3c1a7a2a017089b172b015cff01c7c10a1da4", True),
    "es_obfuscated_payload_2": ("112a28ee72eae9051018853ce10480dd87f3b8e17dbdbb81e2b1f94ed607da07",
                                "a4d5f63979936ec496f05e0c148d7ecbc4cd957b55123a4396283a69465c1a0e", True),
    "es_indirect_injection_0": ("3afd5df02c514bbbf1645234b18537edbfa1224d9948fba661e992abce9167c1",
                                "edae8977b435a2ae00ed81350b3aae395fa6ff6177ed141f15a93dff05a1c9b7", False),
    "es_indirect_injection_1": ("440f259f3ec0f5207bce2d04c59935372ea4b332d41fd684aa8da454a189eb7b",
                                "c99ffbbbbaf61e667feb76ca51fdce9b4dfc4a9ad66e10b23c92c8d6a5d30f35", True),
    "es_indirect_injection_2": ("5c5d3ad17676bcbcb7341def7d4304a25f526afac6ce3080dc50b2363091e065",
                                "e8984918a319a7f081dccf04f2bf9cf0fec7802c4dbaef9e9dbfcb0554805c2c", True),
    "es_control_0": ("5410fdff289c5e3d316e799f8a4e0b67fdf0d9008c8f94b470f7867b41719d87",
                     "bcbd318b7a3f8d784455fe54c26db5614f76d90fe578385833bf2ae4418266cd", False),
    "es_control_1": ("d9d5a7c25aa487028e2353d892493d4e73e86690d2342ac93655bacc08d7e15a",
                     "024ec0d2f5775040c25b450b66f5fd7ff5943b5192b5f7ea3420f16fa9d9c753", True),
    "es_control_2": ("51199363f1b8f29a488ac5f6061b539b7939138e89800156507c2ca464eac731",
                     "7ad72a27182255fd97d77b4e4f10a1d309fe38bf4704426cdaec42c135be3f63", True),
    "es_control_3": ("f2b3f402009bb21830c029750a64255e314bb823a49ee2e025eb6fb44de803b2",
                     "50e8869afbb87d94fe3d2a7e3b8f91093393b18cae220a08e7356adcc351c083", False),
    "es_control_4": ("8dd79e8a78d3ac9c44965c10e9539521214f0fa2f295bb778504bba53429392d",
                     "db8a2f9832f66a52eaf8f3ec4284ba1e9d9ba8e18258b0faa926d0e501440bfd", True),
    "es_control_5": ("d88c6d69551bf8885e9cda6051be1b8bdcdc139a3e3cc23b857bcce95b8083d7",
                     "4a51bd0933a221aeef99704cecc1466c3aaf9a0a5e6a4a63510ed95333dfa91a", True),
    "ar_instruction_override_0": ("d1cf2210576776c3f73a5e5dff3d256f04677eb0c04a3214d8a12a315db75c7d",
                                  "08bc0c2380bc51882ae5bd60c247e9a15c4888d1139b05c16b8f71ca703752e7", False),
    "ar_instruction_override_1": ("28b86a0322897d1b02086a9d36c69f2d7be1a931693234c3a14aea57089c15ae",
                                  "d0b838b2fcc8c96e7c958aeb5b115067bc6671a97dc35984379f18c28a918c61", True),
    "ar_instruction_override_2": ("461c0ec6fad3fa01d9f524516b9576df36aa249bbd6e74cce39de0073d236cd1",
                                  "fb0fcc462607e76262891c2b37343beb9ea0e40a62dec6d215e86439972a6a59", True),
    "ar_role_play_jailbreak_0": ("e1e228700f2360b72283ee806bc88b55ef611a0765949cdf261556ee95c0e91e",
                                 "f90075bea1530c28b3a971ead5dc8836480040528f6ca13bb3a695b07299abec", False),
    "ar_role_play_jailbreak_1": ("84e6c06e42a2273914185c2825511ff193dbe441bff39c45e5f57060c6cfa361",
                                 "7326bcdc1fcc76ee54e620549658ab51a698fa36b0bc4a04816f27e3c1ab01b8", False),
    "ar_role_play_jailbreak_2": ("edd0ab62ef8744ff5fac31c803200d03e92dcc86888df4f3a673bfa25aec37af",
                                 "861a5f11a18b099bd86ea518e2cd21d72d460fae7ce1014a289de3b9311ba4dd", True),
    "ar_system_prompt_extraction_0": ("2fe48535a3a59200b5f1c5ab3ed41216c533244ff337e8e4be7c4dc8b7899d53",
                                      "2fe48535a3a59200b5f1c5ab3ed41216c533244ff337e8e4be7c4dc8b7899d53", False),
    "ar_system_prompt_extraction_1": ("ffa3d4baf24e402f9a3393d68b64446ca913e2e69ac2f3654fb4178c24eb9b4a",
                                      "ffa3d4baf24e402f9a3393d68b64446ca913e2e69ac2f3654fb4178c24eb9b4a", True),
    "ar_system_prompt_extraction_2": ("80bfffa199b31ae78fdef542c93d0da30a6fe20244a36fba2ad819431cb63cf3",
                                      "80bfffa199b31ae78fdef542c93d0da30a6fe20244a36fba2ad819431cb63cf3", False),
    "ar_obfuscated_payload_0": ("ce072036ec9a3c1d67e68116e90ef8a1d98b0cade934aa53060c66f377c6ee7f",
                                "8a12dfacac726ba1e63946831a85f440474d2ab847f7d5710afe3abea64367c5", False),
    "ar_obfuscated_payload_1": ("1fd6ceb51314dce24b89f75af519f1724109cbd72e4c59df73c1db1932ee711b",
                                "bc57f86d960a5a23fb76bdfc852c5b3bd2e44512577d9aa462d982e32421367b", False),
    "ar_obfuscated_payload_2": ("b6c93cbf806a126e3a217eb4a7ff8c9cc523b55ae7fe512345c3c6d263e55e33",
                                "ea6471990f841f4c626313a23c4578767f32bea64e9d9af80732507a4e32a264", False),
    "ar_indirect_injection_0": ("272707ce2f4e284fa5ee5a912bd77b44090b81e54a08faca0eb5cd84cc872d5c",
                                "1dcc2b0fd4b6c0868ccb40d78fbf1515f20bc09a6a2910155148fa8d085b95fa", True),
    "ar_indirect_injection_1": ("f4aabb79ed4993c5a1111661e801c54bc3c76f6417749b78b3d8506b2bce8c0c",
                                "3b68707c7e1a60124189f31e50a23ff874d3768110566a2f214482dd6a7d8e72", False),
    "ar_indirect_injection_2": ("6f0aa89f20d4a41d0c1b434ebe75ac07dca4333fd4ffaf7a545b91a2c1f084bf",
                                "525c9588f9886331afab7c70bf55f7dc5f2b995410531a2c8f316e4a2cad35de", False),
    "ar_control_0": ("161ac089dd231f5c609d3e05b0f8ebce9e01adce22d88b02a35d8b6fa5df0d1f",
                     "28c2040b7de12ade47a1e4c0cb141e950490a79a725f22e4ef7983edfd4eb7f4", True),
    "ar_control_1": ("08913592e19c0d3bac0416afcf0654647fd27fef77900db68acfc31057885c39",
                     "524a944637240197b532f32d9637cc8100225e317cba7eab3c1a8d6920246062", False),
    "ar_control_2": ("ee3f56ccb7c2002cef165839c681a3c9a9a5c2364aeb8aa85fcf669e0c0d884f",
                     "cb3cfd264309c6dbee77b4a605d0419df6c3feb285f0051ed623889f6e1b83f7", False),
    "ar_control_3": ("7ce866fe05180203d112d19e27d23cec23ff099182e3314f588aa508f4b546c4",
                     "0e42e53ff585c2a4b2fe6a06a9a72bdaa9ac8da402780f327b3f11c9c01634db", True),
    "ar_control_4": ("7eb6e0c9f9cabe0fd4bac56939663a6dc53887fdb9d79cd12c4c35a80fac9d90",
                     "d5d043424edd222c3ed59d70f003aec431d45cbea72766bd32252035808f3600", False),
    "ar_control_5": ("b5183822ca8c65041d8f122967709772dd1c4418b9a976f4bd16a0290a7e30d9",
                     "e020610e7e9fabfa639bdbe0818162477fc05c101623294b565512030fe85a2b", False),
    "pt_instruction_override_0": ("94991d505dbf744cc2cfe77bbdab08e8283c823e533b9fbe2016a265036e6b04",
                                  "9f391ad739b3dccb85329d0e08933a99054bf050e0e3566fc5a906d49e8b0f83", False),
    "pt_instruction_override_1": ("299bf8d8e74b36f87be04851789c11075908d91f08bc00f08dc81b0a942b99ed",
                                  "b39698f15a62ef9c820ee945678b8fe1dc9c741dba6ad0812bd1b3d8c8ee0ae2", False),
    "pt_instruction_override_2": ("910ebe1351924d45be72e278dedada1baeeda2487bc61b3bf74a4e9ef4cefce1",
                                  "44f9a633aa4504f55c46047efee88179a315f4b706a7e260d6de7bec33742347", False),
    "pt_role_play_jailbreak_0": ("c5599bdf192f86abea74c69333a16f248ac417bc9208d655d1b60b93cf18a5c4",
                                 "04a4cdcf5cf6594ec107c35e3ce1025a05b51328f29715dcdfd4eef42973d7c5", True),
    "pt_role_play_jailbreak_1": ("5c0f1c074cb7f50ddd24362a278d48ee022cc41fc35c5d93fe6042768a84b938",
                                 "c5c18aad20cbe59a9af7c54fed6eb45e8c6070a3156afa7c03d395a613de1794", True),
    "pt_role_play_jailbreak_2": ("a45aa497c89e1adba633b900cfb3499c0f54e35e8e08fdace7fb578ef3ef7783",
                                 "9a5120ab7f0ee3c23119592d89b343df72a1ef8a12c9f6113e8d3e13b7195791", False),
    "pt_system_prompt_extraction_0": ("6d9b45a724327b2790273a7b998b4f1a11975e54669b0c99d129b780b1d8631b",
                                      "6d9b45a724327b2790273a7b998b4f1a11975e54669b0c99d129b780b1d8631b", False),
    "pt_system_prompt_extraction_1": ("6253a91f251b15772a24b4c0bfcf81588c13a7b28bceb1f398544028954db8a0",
                                      "6253a91f251b15772a24b4c0bfcf81588c13a7b28bceb1f398544028954db8a0", False),
    "pt_system_prompt_extraction_2": ("0b51da1cd97e13d2f164a8247b84bd9d2463685559fdcbb213cacd7ad0fc8901",
                                      "0b51da1cd97e13d2f164a8247b84bd9d2463685559fdcbb213cacd7ad0fc8901", True),
    "pt_obfuscated_payload_0": ("bb5fb48e1e98aae46fa0a1807452279ff40099ecfc32ea1a76719c0476065d6f",
                                "04da3e7ffceeb581bd6324cd728e42b8e0534c3123b09393cba9da7a02f079c9", True),
    "pt_obfuscated_payload_1": ("deb4be099bf2e2e316124cd0495e18d1ea2fa28df045da28a15bfcc43f8ebd8b",
                                "8f6610a6f4dc82383478358373a034b7d87cad46dcc29ee980083bea053e2e39", False),
    "pt_obfuscated_payload_2": ("33e60f824acbc54e090f6411077ee3b1cf80e34abf765613515e59f1d117e4f5",
                                "5f0d9b31b9cf60c96b12a767ee6cdb365d38a87e56d7b3256126d04e91d112cf", True),
    "pt_indirect_injection_0": ("c4d80c4c04f4d6df5048f914e9e580e7e7e0359d8414ee7fe8d372713eba0358",
                                "a578eac77becf4fb9e9bef529afbeee92e12be7ed38f89fefdf8efb791bd8908", True),
    "pt_indirect_injection_1": ("98adac60f7a75e4086cd58a1d841e00019a31be8b149f40b2f37e419a2868ab0",
                                "3bf7822da3d4bb3bec2314cb1826c8f5ad1e86cee216b7017cad65062b462c2b", True),
    "pt_indirect_injection_2": ("98359943af5f7821c1396fc867487d8e86f604dda63aa73fdb604473b3b35fe2",
                                "ef5ef14ba4fdb7800dae3c36f671a3d83e9e0ca8ba3112f917924457f7a68141", True),
    "pt_control_0": ("2730764166e3cb19e4b001d01dd03bd2611ed91aa176e1c88660a4117b4108d9",
                     "fa4a336370240743cd33fe25d75824d61d65b17d8eef92e39ceccfafadf1895e", True),
    "pt_control_1": ("2d2581ac7c132a9d84a0ac134808a118cf0357d593073de09c5666c97db5a791",
                     "cefd57bc7e12787b242c9cc546f30aa7d0f7cc25c5e922a6174bb00bafdcf9d4", False),
    "pt_control_2": ("df4c854bffc64d1a66abe7355a71fb8cb4fedf516a0a54b760661ff2a119d9a0",
                     "bcc97a718d6a5373bf2dc1ca0c2df3388dd87e01b90339db48b9048498b99086", True),
    "pt_control_3": ("18b626b1f4144b713e93e4ca0bcf492c98f458e8bb41ea3ef142b87cdf833a56",
                     "15a7261547b0c9d2affb9ec1ab178d2ec621b5b8bbc98a78b41286ee7e7b2b50", False),
    "pt_control_4": ("51bb924a2c626c278847d4a87847b1bfab99509bec1d49758b5dd2a1e0686e8e",
                     "79e7423fafc9861fb45dbce513c433bdd6b1359e6b69167df8bc5039409c32ae", False),
    "pt_control_5": ("fb842a2a2a0ea3ac75c998590ccea9af20d5e83946f33634bc155017199c83da",
                     "67e0bee5978dd2e3f3784baabf0847c04f766ec9fb21d727edd3faf98263be94", False),
    # French (author written): register made consistent 2026-10-14, controls tu like the attacks.
    "fr_instruction_override_0": ("b3fd8381d734fd6dce7325e8e910be38c52fbed0a4d5224812576dc988ac5ea6",
        "22832f19cc96db78e77534cc28e4a73f4b576dc023e4901012678b133af45fd0", False),
    "fr_instruction_override_1": ("46d619996688820172661867739c89b45613b9d46cd7869ba62077004e5da6f6",
        "fa4e34fe780bafafdd3f86bb21cf48d5eab8df0a6c10f9ef8bf2323cfea7aa05", False),
    "fr_instruction_override_2": ("4dbbcfdbe0f138a2674badea04a05738ffb35f2a2ec24d368b9ea72d7731bf19",
        "044a0950e2689ef4bc635b71108dc998c0d00095bb31430354bf1e80ae15e75c", False),
    "fr_role_play_jailbreak_0": ("3291d5b1d398a4db0579ca8916c56439a2c6753223eb5206c9ae57d33e9bda7e",
        "dc8f87400e44619da93e379ded61743f2442a64938f69f7dbb533d75cb9020b9", False),
    "fr_role_play_jailbreak_1": ("cb6aa5a41d076af497793127ca1155f494ea73df8da94ef710d1b3df3f817cc1",
        "20afd96e1dfbd63564715fa42e3a3139a75aef93ca0bb9275f54eb7b9cbd1402", False),
    "fr_role_play_jailbreak_2": ("e3f3bb32f48807bb77049b685d651cd748e646823d2deb01cc3f1a32e7126fef",
        "e99c86b9e2b17f8a044a9a575e311c599a6becf755313f232f44f87d14aa6475", False),
    "fr_system_prompt_extraction_0": ("5a5d02a9646585bf2ac20c2ec4c262de35dfbd86c6b5ecb5f9c83b36afc990ee",
        "5a5d02a9646585bf2ac20c2ec4c262de35dfbd86c6b5ecb5f9c83b36afc990ee", False),
    "fr_system_prompt_extraction_1": ("e7504b2bac917d2778b854b9eb4cabf675a279abbe8c6237e74fe42a2bb51fa4",
        "e7504b2bac917d2778b854b9eb4cabf675a279abbe8c6237e74fe42a2bb51fa4", False),
    "fr_system_prompt_extraction_2": ("d695f313f7db1e786480b3a9be44bd68b6ae6fa1bf5596ef99e2dfc2b55c0b58",
        "d695f313f7db1e786480b3a9be44bd68b6ae6fa1bf5596ef99e2dfc2b55c0b58", False),
    "fr_obfuscated_payload_0": ("220c46392378f5ab6b9fc57f5dd0355c62bcf9734327ed0ab124b7cd3bebf2f8",
        "738afed198cdffcb78ce75ce416329a28052b1c1d3f284205c1962c2bbcc3f80", False),
    "fr_obfuscated_payload_1": ("3995b82b4f7101041109488fed7a4cbb2c3a4a37f5c734eec6656a74e5fcf996",
        "8ae582ba03f0b875429f141fb8ab9823da13efeea390d2b8153dddf795bad864", False),
    "fr_obfuscated_payload_2": ("a3a73b46a95bf797c015be069de7ce43b68bbe84b1683114bfea56bb1439d3c5",
        "238561a9410f8f43882f936ce314a63fe00bfbbb3c9f32df669c5594285ea847", False),
    "fr_indirect_injection_0": ("e3b76a1121c40d186adbf36f8afd6c59f8b734b725f81bbef922dbdba5715224",
        "f590e42cad807937ae8c93278f154da96a8bb826285b8276dd9429363901ff45", False),
    "fr_indirect_injection_1": ("400f879fd6d2a2bde10be312c735dc9709b62e4d42bed55e9644ebebf4850169",
        "21417fc07198cee671452f0b1b374247f5597e193115b7c8128a8cb062cc734e", False),
    "fr_indirect_injection_2": ("08e7ce027b0822f130a668244150041157bed47402fb63d05facc3a9ec271fdf",
        "d78a762ae58f78b6b68fa987639fbb3f89b0607b40ce734123e78ebf6b2b6784", False),
    "fr_control_0": ("9ac679a232c6c4d26bf95aa5fc4373bc4e7f611bbe808dc28ff923347a66d756",
        "31346cf5b9611b017c8805739d4259e2013b2e0d77a140bdb3edff220657ce5a", True),
    "fr_control_1": ("853ea60b88aeeb8cba725d9cc36ee45fcf47d3febae2318ff508f484f808d483",
        "84e7b148f93301ff0ccfa09a21f24989557311e0d4f658d39909732c8bb4438e", True),
    "fr_control_2": ("78baddf5cfb7df6ecb6e24ac1595908a1c957d5a30a789cdf00fbd2120e0bf8e",
        "d6219ee48d06fdcc7d457576e5cc86fb0cf2199fb1f453551c7d86c4a870c919", False),
    "fr_control_3": ("81e61ec2ac9598c60dae50eee085a6af536235e02b0e76a22fa0ec98ad063878",
        "f84805d7ef45a9a7a90eb20a4fca6551f588f114a21f93533114ad013b24c0a3", True),
    "fr_control_4": ("25d0f11edf31bf194fb1a96f30ac9676e27217e0cca8c388e6b0487fd2f02d7f",
        "ff4a9577d066e532c7407d4839b1a88654434d42b5b4c4b624d3e6257a5f1548", True),
    "fr_control_5": ("c5b92742533412ee3c7f77d8d39c3119905edff7672afcf371fd07456cdcb9d0",
        "4e86af307393fe5d00d2e85c030332b18aa16d0c92a7c6b2ad7bd12a0f40641e", True),
    # Lithuanian (machine translated): 11 returned corrections integrated 2026-10-14;
    # lt_instruction_override_0, lt_instruction_override_1, lt_system_prompt_extraction_2 and
    # lt_indirect_injection_1 are held and pinned at their earlier text.
    "lt_instruction_override_0": ("29694e388048471d1bb771bd9706b9b3e98a25ea76b8eb45cf2b85a161b5c4fe",
        "da193171b22ed1fe4634dbfe4da301874f4d889c7d48b50977b752f78edf99ee", False),
    "lt_instruction_override_1": ("214f389b88fb45759ea8aa3b02e7e1e77d0182c00a6a5e2a592671992b025009",
        "edf99b7e988949899fa45e6dfc573b1f03472e971d4778480a431dca72b0b966", False),
    "lt_instruction_override_2": ("811bf7745124faf7bc5cb06d8e20bf958cdf06481bb024ad25ac5b446840f742",
        "471e47ba3b27a594327e3360aa254c806958dc58bbfcd0749bc856bca9c45330", False),
    "lt_role_play_jailbreak_0": ("307323abd8ec4795c44f10c3b9bd42776d43c2d2a08fccc3e43e7fe801943a00",
        "1fa0aef0bf2223138a06cd38c99b0f99c5b41618649150b0916125d38f95ad18", True),
    "lt_role_play_jailbreak_1": ("36dc8b0eed7b7101cc16c326ec1ade51c311a69f45acbab1945ac54da79349ca",
        "6d942cfcf26d28750048d1499c9b079c62adc6ddff71cbe9482c284bfa146f62", True),
    "lt_role_play_jailbreak_2": ("35300e4569ca70fbcf25115dba9dace54e1d4e39855b4353daaab944d150bd81",
        "a2c8db917a472395cd99e803b4fff89ebe4158349e5ca1e12df01dd6a4f8e46e", False),
    "lt_system_prompt_extraction_0": ("37fd5e83d24f80f305a4a0b34d66225aae044420eb3d6ee5db29057c2d63ca45",
        "37fd5e83d24f80f305a4a0b34d66225aae044420eb3d6ee5db29057c2d63ca45", True),
    "lt_system_prompt_extraction_1": ("927c02de824b00fd6bc9f8991a64152d18d638b47e49c6952f4cafa40227867c",
        "927c02de824b00fd6bc9f8991a64152d18d638b47e49c6952f4cafa40227867c", True),
    "lt_system_prompt_extraction_2": ("5866d243aec9fb77d5f87584710eaf2184ad03cc6a86900e3d83f13d28ed92a1",
        "5866d243aec9fb77d5f87584710eaf2184ad03cc6a86900e3d83f13d28ed92a1", False),
    "lt_obfuscated_payload_0": ("60c66be409ba7b63a78f2d091e4e1256cbc06e7e87d5ffe21fa6bdd3dfe807b0",
        "4e72c56e91a79bd1840026303625197dc570c14e940a54da3678c13dd0078a26", False),
    "lt_obfuscated_payload_1": ("df21346d3e6d05ba0514cfc4de73596e5748282a0de6b8dc9ca9f3928cd1b63e",
        "84a5e87845646ce9b0464e97d40c1ebdbd4e13f544e93245dc430133b47e5277", False),
    "lt_obfuscated_payload_2": ("afcb32b55945b0695ef52e63366750b2de017a38fb49bc51fce08aadda1fe9ab",
        "a1a0ac9774f6b3b9457797b78f8273d27740a7f9a42e8e27578e89750dd63de8", False),
    "lt_indirect_injection_0": ("ea36c7a79cb64687c3974e4bcb7e748d302b2fd61ef91dcdf8cc02d090ccd80b",
        "d5daa477047bf1ea51095963a049a54efc2d9c82702ccd666d6349feeb732cff", True),
    "lt_indirect_injection_1": ("c70dc4ff5b5229f9c746757089b6cf565346e3f1a63397b48ca03b0b42c260e9",
        "d24f1e5250d029021bcf5d0a3c8f327a054470cde294887b343ea5969790cbc3", False),
    "lt_indirect_injection_2": ("4ec9411037008d9bf474883b21777933e00cb5ef1b62003ddcb6627de60d81e2",
        "17e792b65d529fe73ed9f7b954ec6f482f9df039053142b6adee767b1ab03e5c", True),
    "lt_control_0": ("f1a7be7bdb3e73681ac81d2b4cf99e12746cbcc498dc76e1d65924280d164148",
        "69ab548e916c209b0842a090cc1b2c87b46a40652a1f702e9d741d6f10e45a28", True),
    "lt_control_1": ("efa66b730a1f45c6f2fafc4b09a9c5b1c076906745ef5f8e5d7c8e14a521b076",
        "23a7ceb0e528e9a6d58cd75e36af93882db5cc0b5b6f653f9b41376e236572b2", True),
    "lt_control_2": ("7b9ec4ca987dda2fc35d178508974739ed3bc05cebc359ca0298ab5284e6767d",
        "3450c6588797835031d707e1fdeff29929e2940255f600b68ecec0ec2fa46f13", True),
    "lt_control_3": ("608306b062355114fc1817666e5b94e278023cb9398379dd66a7a7618aed672f",
        "754c7159a72ac2d9f1f7bad9133d61d93e4d97d8f5197646601f4716f3e64cc0", True),
    "lt_control_4": ("1eba2adcfe9ac584050854a6e32bb9f3f873509396ae0a8fa96bc382880b8261",
        "89f1bf50b2773948c7b1523b5526e1deed70d2bbd78676c48d2b9607a2749015", True),
    "lt_control_5": ("5a0b06766d5a4d409a28ee92464a5ab906f405b836c77ecf05ae07efe596ae8f",
        "1767bf567bf89afd3c42053f7614782f7d73660f14836cee5c8322181ce33bbc", False),
    # Bulgarian (machine translated): 14 corrections from Iliyana Dimitrova integrated 2026-10-14;
    # bg_system_prompt_extraction_1 and bg_indirect_injection_0 are held at their earlier text.
    "bg_instruction_override_0": ("611ab0ce0fda43a97ed8062b5095ab7324e595cdaba730139b0a0ec52c74941b",
        "21532f74077a253e43e6b02380a97bedcd9361727a116d2ee1df4bf0b13752d9", False),
    "bg_instruction_override_1": ("f73d03e6c3ab9eaba4c3c518de0a02794a101d46b1e24d489ce3f82142e830e5",
        "8a7e41a9bb57219df64ea4d1a4d732dbe59efda59a5b075cfed19515da171bb1", False),
    "bg_instruction_override_2": ("5c2a55b5ea7c0c0ba9841ffd5d7755771545f3666a83abbd500246a8fd90b812",
        "c54ce7534758154fa6aeff270fcb64460bd407a73fa1b9afc44a39877295a157", True),
    "bg_role_play_jailbreak_0": ("60e94900da93a8bfe05a03da65de1f0bbf32afddb20bfb62a343c759e2472e3f",
        "2b2552412e3ec9e4ee75d2194f5c9d4340d9fa3bdb527773577e781bb9e3dbfb", True),
    "bg_role_play_jailbreak_1": ("d455243e20912f62d08f217c895c1d935fbba01c1d96fd107402492618e8c4ae",
        "08bab23c9e48edbd9b97c371d82f62f9973b5a4ecca741a9768ca16f4bb47631", True),
    "bg_role_play_jailbreak_2": ("83ca3d4005278395b5d3fbf19592c5bfd7817d8662976b874646e1a5cb3e00bd",
        "12a33c7bfd07e82b3acd622c935b02124af43b6aa75ade0342affb3ca95d7728", True),
    "bg_system_prompt_extraction_0": ("7d988d61d7c5aa2a5d73871242e207abe90d91629bd3731903b632ab98593c93",
        "7d988d61d7c5aa2a5d73871242e207abe90d91629bd3731903b632ab98593c93", False),
    "bg_system_prompt_extraction_1": ("d2efb76cbad6d741371ec1eb4c1efe20ee3e1360badb973716abafa0e3cb6aa1",
        "d2efb76cbad6d741371ec1eb4c1efe20ee3e1360badb973716abafa0e3cb6aa1", False),
    "bg_system_prompt_extraction_2": ("4c21798b6ab05922b89b4a1e26d67a4e6a8665a0f8894304338c44231d91970e",
        "4c21798b6ab05922b89b4a1e26d67a4e6a8665a0f8894304338c44231d91970e", True),
    "bg_obfuscated_payload_0": ("d89d8766a60958f42ecd2bfc1109e3e537bfc0c7eddef10807a8fd31b6f5e6fb",
        "59f826d6dbdcd1157736ff079b469517591d85fca891e287017d8a17d11a6a6b", True),
    "bg_obfuscated_payload_1": ("5697941dfd3cf318ade0879c265a3c815dd109907fc12342c84fa23b86579243",
        "e2370483a389389d76760e24de6da370811f3094a18ffecf86953e0f0845dba0", True),
    "bg_obfuscated_payload_2": ("90f7533825ca881a3e9ab9d1dfde56bc1e125f04a94f24b9e813c0b9048d9e0a",
        "cade6cc690f701b999ae980c0bb804d61e246ea7e40de8be9255804a91c21d6d", True),
    "bg_indirect_injection_0": ("b0d1c13f331c3a2073f76d3b76bf30b986b535e58e82a16e9391772c608d99aa",
        "23ac1c849c3dcc3cf063249b2b8904b9b57407c9f9c1649e5c1fbabdb2fb71c2", False),
    "bg_indirect_injection_1": ("c18076c65a2dcb3aa35389ab2a9e419c20109a294fc91ee8e97d6452480d24a5",
        "37191e03f9374ca1fa3ef62a57af4d284caf493dc3e6b8251543244e72d25780", True),
    "bg_indirect_injection_2": ("8013df780dc3cf56ac0323b8415c07d2b7826f810b8ed448da93323fbc14ada3",
        "dbf48d254f4234315751d0de558ac94ed6e9ab4ec36632967c26d436e5782f6f", True),
    "bg_control_0": ("e1d625a1a640f1c42ccbc2fa25ec45869e3de6db08cfb8dc6532d8decd9423cc",
        "b79a9689431e0f77781e0e7bea336c359293dcef1f22000c7e292b1b3415a914", True),
    "bg_control_1": ("db915c0935a49b14f0ec3b61f7cd613171710a3d72bdc11ac65f77618587a466",
        "84e03bce40d9568b28b92521278b5ad7c1e6552a79ea58300c916ba4affb17c4", True),
    "bg_control_2": ("a5fec8f92027a7b0487d3560b45297d50aa1245a1fd566a718a36e1471c45a12",
        "0560431fe78f38cbe679655fec663c786cfc4b3db9a19bfa51403b9f34ed6a67", False),
    "bg_control_3": ("2b65868c1ccd5c7f0ed9c66b8cdf5e0c08b95113ea0a93b2c3f1329286140b3f",
        "a8b343c44a8adb2c9b30aabd7d679c7905d76fa72593bfbf4f1cef711e9ee77e", True),
    "bg_control_4": ("c4c2e502012dc736713fa2c430d6082b5bfc12b4f7921cebfb042d50c5cfd38f",
        "ff7df4b46947d561e586383de6ba53f1d02a96bd032b6e00f3d841036f52c512", True),
    "bg_control_5": ("c0e6f13a92d8d9cede23aafcc016239204f3dac0f7cd68352cd2b025a8595197",
        "3b3888880d2c787ad2458ed442b643b865f19483b8ed785324110302a975ec37", False),
    # Vietnamese (author written): one correction, vi_role_play_jailbreak_2, applied 2026-10-02
    # (commit 99a3091) and pinned from that commit's text; the other rows as they stood on 2026-10-15.
    "vi_instruction_override_0": ("1c8aeb13253c9e9c76eaef629b21a85e78664d2e9e87ec65e6e086872517fbeb",
        "f84836874e8011338a4f45cb706c4dfddddc9cdf43ce0a5e3097448477942b67", False),
    "vi_instruction_override_1": ("3a3f027d852427497cadc44c7e908b0215e8c492dd6475127eaa38120a6fbb4d",
        "cebddd6099312efa2810de55d52fba7b17850ea2c7a021f38080f440d17cb46b", False),
    "vi_instruction_override_2": ("90a17bee2e36dd678f303c05f313e2d6c9b8903e6565445e4fd10824d1274bac",
        "d759dbc57112f650fa4b96dba0185b54e6d735f38a7800bd459a6a201f4fb8be", False),
    "vi_role_play_jailbreak_0": ("6286c9e204b8d256af7f21c87578dbbd835ae30c22ad29d7f5e920f3d71685cf",
        "b82051710b5661ae898355ea641925d8a9ba759a86039535961fd7312b8826f1", False),
    "vi_role_play_jailbreak_1": ("66331ab6cbfa3518407b0357a85132b31de8440b902104280229557b70b364f3",
        "21aa3414de91175feab9dcdc2134033ec3824e0794b8b0c5ac2634ee1e0bfb79", False),
    "vi_role_play_jailbreak_2": ("1c09911715fafb4649e09718990ecab80f4192ff6c6238c94cce9597c7c6a2a7",
        "faa61083f75dbcd0cf8625176dcb00f65875e2133c09ab4194daf44d743c4c1c", True),
    "vi_system_prompt_extraction_0": ("a522ca03559b9ac55823abe5542e9db71e9e074c12d029875419bd2056db9779",
        "a522ca03559b9ac55823abe5542e9db71e9e074c12d029875419bd2056db9779", False),
    "vi_system_prompt_extraction_1": ("e7ecd7bfaa2829451cfe5a686d28a5dba019658d957ff23fdc036f3bdd235748",
        "e7ecd7bfaa2829451cfe5a686d28a5dba019658d957ff23fdc036f3bdd235748", False),
    "vi_system_prompt_extraction_2": ("32c62c5214d86e64a3f16bbacaf2acf31e8611d4b88860ab7c91ac4af99cc9a2",
        "32c62c5214d86e64a3f16bbacaf2acf31e8611d4b88860ab7c91ac4af99cc9a2", False),
    "vi_obfuscated_payload_0": ("6ba39b548ba5b6adfae44cfc0ca21cb635f32382fa580aba9c626ff20302b899",
        "37ae3f793635aab8e5bc550e0133f1e6a829dc36ea7cecbe607a4bd8f78ecf64", False),
    "vi_obfuscated_payload_1": ("bd151e9146b9a881807cd93294f849316d2b9ceb5b686371549d0a4ef7248029",
        "8bf9a8c0663606f5e12e0886e8dbce510a3cf42fe7007c12210b943510462cf5", False),
    "vi_obfuscated_payload_2": ("afa3eec8a8653eaa5da972ee134794f2ce9c2f5d1c6f6fc90286ff1cfee9eb61",
        "6c2129cc4ea947f8f79bc6d4e9f1fdab4a537b70e12cbcb264eaf2e213c26281", False),
    "vi_indirect_injection_0": ("ee3dddc2f1e824c2dbe96849de7bf7eb138ea1f9e782364d6a4e6d2aac436e77",
        "bceaa6fc9336c516cb89c54c0c0366fbfe7cbd9a054c5a8cc9d8a554ddd36394", False),
    "vi_indirect_injection_1": ("5ecc8d4b4f0bc0b79f371e50a1f4867079186ab571762f19aac7bc2850e3cef4",
        "40687951f2054ed09cabffbc98a87f1f9d2d2042ee6bc231ae8b3f2b24d53ef2", False),
    "vi_indirect_injection_2": ("aec88de54b7dfb6330a51d7049920a3609d025849ad56cc1abac42fbf2a7f8bc",
        "a487e7786729d1812b070ace3e1918d8b4aea80b0843378906039eb3ba690735", False),
    "vi_control_0": ("1eaea48b6b5d2c15e06042968504bd03f5e6f871d8683f9731e13459d62f76e5",
        "b8e79c690dae2e55d86909a50e986f8d390442796782ebbe8566ccb54b6fa8b8", False),
    "vi_control_1": ("b8c337449ef8f2d7bec37b2419061eb9c60ff80b7d0461c96637645dd22646e5",
        "fbf9093140ea00a7afa409db44c33ee9b1d261483b2bc0278b9df73140e3121d", False),
    "vi_control_2": ("4944aa9d939120e0f26b20faf8e5c562531ca4ac8b30f2345f6b70bef8fbdd93",
        "9bf3cbc12f38769efd1da1e15f63a493e0f612392d6b2a277b45e7d84a987e68", False),
    "vi_control_3": ("7cb0c697c98302011bf91d8b5f21a72fd5c689f1300ab991ab6fc3088d33db6e",
        "c05e8401322359fc55aab27fe4d95ac3fb907cf2737fb1ada82e6120ef698960", False),
    "vi_control_4": ("5b02331096c98c0011abe907274e11e27b45b65006c123770520bc7a6156b4b7",
        "5246b9e78106299123b602045f57c2d5f7630b9a8f346a48f69f013205180357", False),
    "vi_control_5": ("15cceeb998ada177dc2ec2dfdb5e3db9f0cd599ac8fb409dd550c496f2da54ed",
        "1be395e6b62f97962e3c73ddb71388a4dd48d629491bae3423582223a5b09fa0", False),
    # Icelandic (machine translated): 5 corrections from Finnur Friðriksson integrated 2026-10-21; is_instruction_override_0 held (Base64 plaintext).
    "is_instruction_override_0": ("bb87382420ae2a14f630b7959a837b88cf3cd6574026df20f5ba70354177313c",
        "f096c19715e8ad458b9a16f58f71d556de4a11f81e13538b166fcca93822dc92", False),
    "is_instruction_override_1": ("4aea8c049dcd42e872b3a0df252eaff1d3e99d5fdc7ac7ebe49c5b76971b5c2d",
        "3208d226143bc0c02e52d987adf5ab5b1bf422b5467f4447564b14f020eedf2b", False),
    "is_instruction_override_2": ("03264fdc1cbb36140fdb17ea2005dc6e5ff2389f677cd2a3b4d04a006b15bca8",
        "9b8355a3a8e45f8fcb917a92a6812e6849d631feca0fcc0fabcb571494a1683b", False),
    "is_role_play_jailbreak_0": ("89316dbd09996213ec1754deeadd5e948127c1c1fc9a60e8191dd0aa864ae43d",
        "394f863a4d2992f771961b9a3926353b40d38956745d1985a6abf26cbfc594bf", False),
    "is_role_play_jailbreak_1": ("fa7f2d1eab3ec0794149c2ee6f0a1cdbf612021d038645eb0d137f40e9cb6f15",
        "51abadb1f9f26aef5f6fa1310752303bc1badefeaf374cd2e629a08a01bb05f4", True),
    "is_role_play_jailbreak_2": ("4f23b9b2db0ae8bba798ac558b5b44e4adc32bac20d8af7c2140fa1c52aa0fa5",
        "6d5d5b5e1ef2d46d1b6ca1b04bcf1db4e8a9f1aaf6d1f40eefc5555a7fd20ecc", False),
    "is_system_prompt_extraction_0": ("dc1e06a826f2bb1e154980db07d389f6977061ab0d2ecabe1a0b1bc4272a235f",
        "dc1e06a826f2bb1e154980db07d389f6977061ab0d2ecabe1a0b1bc4272a235f", True),
    "is_system_prompt_extraction_1": ("337029484cf3f15f73aee19fef341f54a1f51a2bd543d7955c0346ac2dc6e065",
        "337029484cf3f15f73aee19fef341f54a1f51a2bd543d7955c0346ac2dc6e065", True),
    "is_system_prompt_extraction_2": ("a8ac8f4a55679c5877b4ae92f6821710b81f76623784fd8419988d086c8b9243",
        "a8ac8f4a55679c5877b4ae92f6821710b81f76623784fd8419988d086c8b9243", False),
    "is_obfuscated_payload_0": ("28be27c9773286822f84872d78fd5e614a1dd2f28a623d298b8b20a4a58b900f",
        "37af2f9ab8854db0dfba4bec7fd66b7aaef5c53f4e0a1e2e40f892278b0f53f6", False),
    "is_obfuscated_payload_1": ("db6fa3d8a8d261af4baa28d24480a1e573a3f99914f49db33a200c03f174e064",
        "0e995d258fd4b20a0a3dcc76e668674a5e5a50d74030daab3f36a375570b0eb0", False),
    "is_obfuscated_payload_2": ("74575b740b8e5a9ecb053f4a8790a27729e68a1aea7d46974a85baedcf105807",
        "940df00213e5ca059e66ec3761592a8b67371fbcb0b4aeb8e99f177bf692be03", False),
    "is_indirect_injection_0": ("c2fd8cb6503966eeb3271199776ec4087c21d1145cf4b142e166dae45f675dd2",
        "65de961f8c6781646b9fbc33669714060e39fef1f095dbacc8f52c64f6b61c93", False),
    "is_indirect_injection_1": ("213e62c1aa5171a423d908efce06abe7226bcfefa31b58832fe5a8893834587c",
        "d83a356ea18cbbde310fc8b2437d41bfddf787d468382844c572904881a4217a", False),
    "is_indirect_injection_2": ("11bc8037fb2f6e05277d7f0aa2c573fca72c71e1fe540a10958636d5ca95b554",
        "5770213746856409ebc5590eb1e36aef0cba652ff7a094c42ad313ab64534cd8", False),
    "is_control_0": ("16b8100e48c63c0ee669e643b369c9ca3fc97588e1f046f7e5f5f0c49999f6fc",
        "80f3e9331cf09ead97879eadf6d5d8e92ea0567637f771b2cf299e57932c13f2", False),
    "is_control_1": ("8d75c4fa067c32813e036d0a12803894684778f335c48c6bd2b314f450d23a91",
        "2b8881853b6b0d4c5dc58c9fedfd634f4898eb15f2d9978203d284e5d56d57f7", True),
    "is_control_2": ("d4a9197fc1c7ea9b8b9f98d4f11c4c9746a0fcbcba7fb694aa9cc20a7d9531fb",
        "4502424d929e2052b7056919219787b0dec1e8c793dec74facbd717be870e748", False),
    "is_control_3": ("5861f2a431df075d99c7da0984f5bd1047a9ab7c4b9f2273afb1620739511f3c",
        "f1265c24fc11a6807ab5457134f437cb5c401da9d7c45322d51cda7c1496ffdf", False),
    "is_control_4": ("e37b84108049bc6ee866414962837a4be714246fbe342cd3f152b0a398d0435d",
        "dfa3302ceadb895539e9bc06a9189e6ce62c1e72b3546fd105e2a713d3ec59a1", True),
    "is_control_5": ("3c51ffac1ff30d3407751c90e42cd836a332bf0d09473cf3a74738412a096894",
        "0a427acd09d089d18be35728118591623120edb0feacbf66bb953de338597dc2", False),
    # Serbian (machine translated): 16 corrections from Marko P. Milovanović integrated 2026-10-21; sr_instruction_override_0 (Base64 plaintext) and sr_indirect_injection_1 (task) held.
    "sr_instruction_override_0": ("ba1d7b2a6014c984d3280190360f00c3a6ae1f8cb6803551837c77fd9d0c691c",
        "fc6d3b922c2a72b6e464e38cce659345d3e8e754c3df74922d39f689140bc467", False),
    "sr_instruction_override_1": ("6b7bd97abac0ce40a39a5f46963142cad7c705182173c74189d87c4d4c6f5a8f",
        "89e9f19b9744c1c6adbc126fab1f783394a28f7f4ec1149c27664e70f38a87b8", True),
    "sr_instruction_override_2": ("8e2992b8a54db5cbd1b504c0e2848f6394fcc9aed6f317185bb79f5f5fcd0349",
        "b5b712ca24eff073f04b6955272f09d72ddaf9c54e7f447bdd7ec868958e0ef0", True),
    "sr_role_play_jailbreak_0": ("0aad26ba6c961fd42fecd3ef28af0cfcecae2c328eec5eaee46877fb1b697a37",
        "5dd83af6b37c99a020a3fe0166a203c334a35a81d5737471be7850a11f3b5ec2", True),
    "sr_role_play_jailbreak_1": ("5451f031400552414880c6dac7c0a1bcf3c2bc251c4e7f3904ac985251d7120b",
        "98f38f14e460e5ec69918df84ae72de6c1cca60122a4cc564367e71bb82bad66", True),
    "sr_role_play_jailbreak_2": ("d92714bd6a9b54153cd669a9ebb5c7ae1b361ae17a2768a29008a62320b7d0c8",
        "17f9c60a7e4c6bec275680b9fad29b90a4f284a2bcdaccbe8c34009c933ac6ed", True),
    "sr_system_prompt_extraction_0": ("10474885233fc5c0744322509d7c743c877b8ae8f7d20c86072dac613617711e",
        "10474885233fc5c0744322509d7c743c877b8ae8f7d20c86072dac613617711e", True),
    "sr_system_prompt_extraction_1": ("8d682923dc2e0a39d240f67435f512dca7ac7cea2de67086e56733f83869666f",
        "8d682923dc2e0a39d240f67435f512dca7ac7cea2de67086e56733f83869666f", False),
    "sr_system_prompt_extraction_2": ("44749071d57b6e0e04ff9fe61cf1cf0a8144e58117c0b0efce6c7e0fa8375dff",
        "44749071d57b6e0e04ff9fe61cf1cf0a8144e58117c0b0efce6c7e0fa8375dff", True),
    "sr_obfuscated_payload_0": ("20516f4dcf55e3343d09ef5570ff2f1e7630e6abcd542da70e96ac172a2c8218",
        "8df579a4f27cc077d7ce70ca0703d6a517a466fe6df91f63bd26a5c7d59476c5", False),
    "sr_obfuscated_payload_1": ("606c2abf7f9f20e69a8e7823a415ea2cad8d49b63aac20ccfb6e6fb87dd95f4a",
        "5b7654d5f6a567f28d85a20cf1c8698e50b2d601b7ab4340c8ce53c46a58ebcd", False),
    "sr_obfuscated_payload_2": ("a1de3196349bb727bfadeab2f4a2c47cbd3d09b8968966a90e080b4b54cea8a8",
        "e45168cbf2b9009ed1c40fe0819f8816dbecd9ffc5e54924920c9e7a23013d4c", True),
    "sr_indirect_injection_0": ("5245975afe1d3338b431d8315422107391bb1daadb5d70637ffd1d216fd61a41",
        "89311ed732fd25be723209da6b72c8954e4adf93b003ded925af889a466b1492", True),
    "sr_indirect_injection_1": ("d2305e00fdd41edba84a1ac46d998242c184830b06de7a10cf636c6cd2f88878",
        "ce97e1e938acfd66d613cf4bf4dc6416f76aaf967237bafafc9096da7aaf72d3", False),
    "sr_indirect_injection_2": ("5c913788a59a71a75db3c9ee76ba8231c88994b7bbdabee54b007a01ffaf2c45",
        "cb084e1c359f82f62cfd3c6d76a8f2d02c6fe10ad1809bd2ffba604c0c630cac", True),
    "sr_control_0": ("9ef0f63b1e97b6ba5b3b9a69796e48e6d9e74839d3b26b338d9c938d3f4d56b1",
        "dda9ea089b26d4ebe486aecb45f22eb815766881e2f62f12c019408d1a17cdb6", True),
    "sr_control_1": ("564a98364ea7ed0cb4d62036e15334cc5d2f9856d2c72aadd2875c9bcac68238",
        "8e25bf3bb01daaf8cc60129d83210967005dd0b0f9c36bd272eea25ea1343832", True),
    "sr_control_2": ("b1ed0e366987a69db2ff1d1cf67c4b2479480c86ae583a8f3b767f3d198c5a2c",
        "424d6d6cfad66c10fd0f5acdd6efacfd5bf6a8ed0586736b424d76b751e354d3", True),
    "sr_control_3": ("a54ea0e2f16cf61c287888fa657f90a35875ee08fc310cf140396a8f2d10aead",
        "29ee36114e9b71147a19f1cbe7d1f61a565c6801ffd47b3ddf35b0e513bcb6f2", True),
    "sr_control_4": ("a531855718f2b96154366b7274c650f11174077481d075703762e6ac164f9771",
        "9f011b6057b408f2eca25304f3ba73e8a81af050550132231149943836539919", True),
    "sr_control_5": ("cf1e9955cb0582ebab2fa05b6bccc5cc915f8f11d8f550a325222ff0c12ff12d",
        "8e8ce1142c6ec3eabbe6a5506ca7e55a2f42ec58055c2fb1b0325163ec8a325b", True),
    # Croatian (machine translated): 15 corrections from Marko P. Milovanović integrated 2026-10-21; hr_instruction_override_0 (Base64 plaintext), hr_indirect_injection_1 (task) and hr_obfuscated_payload_0 held.
    "hr_instruction_override_0": ("57de2f917b9a5f2512c1cdd645da55e32bfd9f4c2e7a364fb245eb2ea18ec2bb",
        "511e8030064b646de1a4073d81af0788437e0907f44a868425480f79807d8ae0", False),
    "hr_instruction_override_1": ("63ef2325fd3354749589d26e5b18886f5a1ce4352401d9c39895b5ab37d3649e",
        "87951224bf07de62e4952e686f14277f6e77dbfd8dd46f753a181431fb2a465d", True),
    "hr_instruction_override_2": ("369cdcb7c3b3364a5e66dc1998f860fdea813068a6615404845b27ad3300200f",
        "2a41c3d93c08aafa72768fa38651c71d4e2150b542c26388981299324c6e164a", False),
    "hr_role_play_jailbreak_0": ("f9003c2355ded6bef8bd2b90c80f7a9eece000205ad1d4d0873a3b4c1d1a3643",
        "dce86109ffc00821580314841ec21dd6b225403aae1b3ae54c0328142a991dbb", True),
    "hr_role_play_jailbreak_1": ("ee0c4d206bf2ebd670297b67d4c7b664d74584b3ec3af2c6f5842628bc7c0f51",
        "0c9a6f5a7e938120c07eeccfee549e28cd359b5f8b996a91628f511100db8c15", True),
    "hr_role_play_jailbreak_2": ("90966389a8212defa8af551aa76659dcc3afa7bdfc60f1f76f0be9c23151fe77",
        "bef770ce2e46c2fc4329de5034037ee0e9d4a237c24b6b48c5c286653011a4f2", True),
    "hr_system_prompt_extraction_0": ("d170ff9f18e022e330407e1d5a0247104960feb93b37f4da722f66320e9ecd65",
        "d170ff9f18e022e330407e1d5a0247104960feb93b37f4da722f66320e9ecd65", True),
    "hr_system_prompt_extraction_1": ("f5f90603b8427a1321395ca646f3067f6341d45fb5fb6630dbce8a3a4d3d238d",
        "f5f90603b8427a1321395ca646f3067f6341d45fb5fb6630dbce8a3a4d3d238d", False),
    "hr_system_prompt_extraction_2": ("f39f0d480e64b22d8c4fbe3e8f51e28eda64cf3518c5cdbbddeb394aa80a7d84",
        "f39f0d480e64b22d8c4fbe3e8f51e28eda64cf3518c5cdbbddeb394aa80a7d84", True),
    "hr_obfuscated_payload_0": ("53e10347097cd7be93c4b6291ee283e84352b11c1434fd26a50367f348f514d2",
        "fd53c702b8b984c82058bb6d6e211306de7497eadad71ed4c6a3729361c6d709", False),
    "hr_obfuscated_payload_1": ("3db7be2930cabd46f46f55e1ec82916f88a51090e7b726a8c525f1d880fc0be5",
        "bee06d06e26e76065c6f8e434aba91f3721264fbe50862a1252bbb741773b6be", False),
    "hr_obfuscated_payload_2": ("4ce5e7ace4480c7eda1c317aab20d39d829ca63452bf46baed7c56b6bc685061",
        "f98b71e5f46389cbd98b8f86caf9c596c0defa976b3a8fe01e2d36ae82579fcf", True),
    "hr_indirect_injection_0": ("e27df32f96760309844986a8649b47c795eef888cab9aa1b18b587c7654507f9",
        "14058bbf18091324f72949b9669b9a869b53233ad9a607a17362e8964c68717f", True),
    "hr_indirect_injection_1": ("9f9dc8d9e60c41b49bb9af6c9ced6eebd791afaf7fe6f9025e9f0a570e174f72",
        "ef4a58358a4bb0852264625948367af59d8f3222735107d7e5bb60d09e3e9ae1", False),
    "hr_indirect_injection_2": ("68e7984dc9a6fbdc787b6d48bb7f5a3a449394205408f2ae59029359813589c6",
        "3a1ccf77b47400f8c9635b8dd2ffd780ae57b8b026e2b13ab5efdd4adc92964d", True),
    "hr_control_0": ("34efe19b58a81981939843ca32499b234adbc458798f545588d2c33837c4e1b8",
        "19831f8119bee2448b7edd6fd36454ca0b2353431abb998c52ff764cd2035710", True),
    "hr_control_1": ("f8379b4020512df6e42f5aabfa421ed75fbafcf6bf42c38dd51c1c9c2ead20bc",
        "dcf7819c481f6876c9a43027a039028e195a51970e46dca77f9a07cde29dcedf", True),
    "hr_control_2": ("978f72cbd4a521bcf498d6c332b607fb22f30c7185245065e6fdce0ba11ec5f8",
        "1df621b9e4322c8977fedab6d110fc1948bb1f44414cfe10718513e1148551b9", True),
    "hr_control_3": ("6b0fb01b942453f352d4932a9bf88349336ad81ae957f08a78d98b9667220cdd",
        "2dbaf1b1996d073033ffb453b14d30701770fa46e72a3ef91266e63c0b683940", True),
    "hr_control_4": ("ab6f24419757311711c72af29ee823aa69354922875a0402445ff6283af6aad9",
        "8763a3e47069ce9e30f339bcd9da400abdb32471058a9e682a583e4fa714aeaa", True),
    "hr_control_5": ("4fae111afb72646cb0df2c224b3827bf0e86caf81badb7c20ad183f2a6acf2e5",
        "3955cf44d16c2298634a9a58257870cb84546eb8301814d8a6653d9c32b06fb6", True),
}


def template(row_id: str) -> str:
    lang, rest = row_id.split("_", 1)
    cat, i = rest.rsplit("_", 1)
    return CONTROL[lang][int(i)] if cat == "control" else TEXT[lang][cat][int(i)]


attacks = {a["id"]: a for a in BANK["attacks"]}
controls = {c["id"]: c for c in BANK.get("controls", [])}
bank_rows = {**attacks, **controls}

check("exactly 94 corrected rows are pinned (es 10, ar 7, pt 10, fr 5, lt 11, bg 14, vi 1, is 5, sr 16, hr 15)",
      sum(v[2] for v in PINS.values()) == 94
      and sum(v[2] for k, v in PINS.items() if k.startswith("is_")) == 5
      and sum(v[2] for k, v in PINS.items() if k.startswith("sr_")) == 16
      and sum(v[2] for k, v in PINS.items() if k.startswith("hr_")) == 15
      and sum(v[2] for k, v in PINS.items() if k.startswith("vi_")) == 1
      and sum(v[2] for k, v in PINS.items() if k.startswith("bg_")) == 14
      and sum(v[2] for k, v in PINS.items() if k.startswith("lt_")) == 11
      and sum(v[2] for k, v in PINS.items() if k.startswith("fr_")) == 5
      and sum(v[2] for k, v in PINS.items() if k.startswith("pt_")) == 10
      and sum(v[2] for k, v in PINS.items() if k.startswith("es_")) == 10
      and sum(v[2] for k, v in PINS.items() if k.startswith("ar_")) == 7)
check("every row of the ten reviewed languages (es ar pt fr lt bg vi is sr hr) is pinned, and nothing else",
      {k for k in bank_rows if k.split("_")[0] in ("es", "ar", "pt", "fr", "lt", "bg", "vi", "is", "sr", "hr")} == set(PINS))
for rid, (t_sha, r_sha, corrected) in PINS.items():
    kind = "corrected" if corrected else "unflagged"
    check(f"{rid} ({kind}): generator template unchanged", sha(template(rid)) == t_sha)
    check(f"{rid} ({kind}): generated bank text unchanged",
          rid in bank_rows and sha(bank_rows[rid]["text"]) == r_sha)

# ar_indirect_injection_0: only the framing clause was replaced. The quoted review
# that carries the injection must survive, after exactly two newlines.
_ar0 = attacks["ar_indirect_injection_0"]["text"]
_frame, _sep, _quoted = _ar0.partition("\n\n")
check("ar_indirect_injection_0 keeps one two-newline boundary before the quoted review",
      _sep == "\n\n" and "\n" not in _frame and _ar0.count("\n") == 2)
check("ar_indirect_injection_0 keeps the quoted review with the marker and the canary",
      _quoted.startswith('"') and _quoted.endswith(CANARY + '"')
      and "SYSTEM OVERRIDE" in _quoted and CANARY not in _frame)

# Tokens and markers survive in every reviewed language's rows.
for lang in ("es", "ar", "pt", "fr", "lt", "bg", "vi", "is", "sr", "hr"):
    rows = [a for a in BANK["attacks"] if a["lang"] == lang]
    check(f"{lang}: every canary attack carries the canary once",
          all(a["text"].count(CANARY) == 1 for a in rows
              if a["goal"] == "canary" and a["category"] != "obfuscated_payload"))
    check(f"{lang}: every indirect injection carries the literal SYSTEM OVERRIDE marker",
          all("SYSTEM OVERRIDE" in a["text"] for a in rows if a["category"] == "indirect_injection"))
    check(f"{lang}: extraction attacks carry no canary",
          all(CANARY not in a["text"] for a in rows if a["category"] == "system_prompt_extraction"))
    ctl = [c for c in BANK["controls"] if c["lang"] == lang]
    check(f"{lang}: 6 controls, each with the control token and without the canary",
          len(ctl) == 6 and all(BANK["control_token"] in c["text"] and CANARY not in c["text"] for c in ctl))
    # The Base64 payload hides this language's own variant-0 instruction.
    loc = TEXT[lang]["instruction_override"][0].replace("{C}", CANARY)
    want = base64.b64encode(loc.encode()).decode()
    obf = [a for a in rows if a["category"] == "obfuscated_payload"]
    check(f"{lang}: every Base64 payload decodes to its own variant-0 instruction with the canary",
          len(obf) == 3 and all(want in a["text"] for a in obf)
          and base64.b64decode(want).decode() == loc and CANARY in loc)
    check(f"{lang}: ids, categories and variants are unchanged (5 categories x 3)",
          sorted((a["category"], a["variant"]) for a in rows)
          == sorted((c, v) for c in CATEGORIES for v in range(3)))
    check(f"{lang}: native_reviewed stays false (feedback integrated, not validated)",
          all(a.get("native_reviewed") is False for a in rows)
          and all(c.get("native_reviewed", False) is False for c in ctl)
          and not BANK["languages"][lang].get("native_reviewed"))

# Bulgarian: the review changed only the wording around the Base64 payload (rows
# 10 to 12). The payload itself must be byte-identical to the one before the review,
# the same in all three rows, and still the encoding of bg_instruction_override_0.
# It is decoded here as data for the comparison only.
_BG_PAYLOAD_SHA = "4eea01711119a684cc145730d0fd49fee5530692d95891cf744fe604b5f16ebb"
_bg_obf = [attacks[f"bg_obfuscated_payload_{i}"]["text"] for i in range(3)]
_bg_pay = [x.rstrip().rsplit(" ", 1)[-1] for x in _bg_obf]
check("bg: the three obfuscated rows carry one payload, byte-identical to the one before the review",
      len(set(_bg_pay)) == 1 and sha(_bg_pay[0]) == _BG_PAYLOAD_SHA)
check("bg: that payload still encodes bg_instruction_override_0 exactly",
      base64.b64decode(_bg_pay[0]).decode("utf-8") == attacks["bg_instruction_override_0"]["text"])
check("bg: the two quoted-message attacks keep their frame, one blank line, then the quoted message",
      all(attacks[f"bg_indirect_injection_{i}"]["text"].count("\n\n\"") == 1 for i in (1, 2)))
check("bg: FreeBot and NoLimit keep their names", "FreeBot" in attacks["bg_role_play_jailbreak_0"]["text"]
      and "NoLimit" in attacks["bg_role_play_jailbreak_1"]["text"])
check("the bank's inventory is unchanged: 73 languages, 1095 attacks, 438 controls",
      len(BANK["languages"]) == 73 and len(BANK["attacks"]) == 1095 and len(BANK["controls"]) == 438)

# Every language's text, as a digest of its sorted (id, text) pairs: an edit to any
# language nobody meant to touch fails here. Updated only with a deviation entry.
LANG_DIGESTS = {
    "af": "5475563e8be775e89d23720d374ab0f81999f727a657cf2b5188729875617827",
    "ar": "146cfbdbc6b02b3b00e97291eea53a286f8ce3541678ba4efa3b0ea4400f9008",
    "az": "44f9e37a8b08bbd03272f60df8bc60fe249200742fc5aed80c394f4c692cafe7",
    "bg": "812c9cc9b286f404a65adce1c70ebf36a7c34669bffbd0984ff5108efcd2bd6a",
    "bn": "b91d79e9438e80e4a6a24ee1472e83240b52afddc7c1127f52e715f1d29be22b",
    "ca": "2026d33291bb8fd9de2548be173de69e32427f119860deb790ab6b63e06ad2ed",
    "ceb": "543401ca445bbc3ee8bc2dfb0a471588563d11b1b6fa00ec30b49104ef7f5773",
    "cs": "45a65c85d0ef1e1e82e71f7c20976bf4a5a3dc1eff7d9240dc609ff685c14499",
    "cy": "d16509f0a9b551926cfd1c77b4f42dbde8d2025ff52acdb558dd74cb533ab186",
    "da": "d1a185208cb3d0386725b28a200926f5d21a33fe3e522b60f4f570387d75293b",
    "de": "a261b5c263f6d2dc54a77acc9d053de2f1d644bcbc49786c8ec5e6aab2e582a0",
    "el": "d1fca607988cbed2449e9b8f0c5ca56772c043613c2c54fc90dbb64465daf77d",
    "en": "480dc4ac5d0ec21b88caddf62714d069195dc1ffe6ddad5c7c5b3656511dfd9b",
    "es": "e5d874df468d3e52b4703d1fa2f1cb4d4624b6e20e269da0e371032f234eb936",
    "et": "9b699203ebdf24b63820c959f7a91f1a68df8168a896c006586937cf8fbad399",
    "eu": "9501a8a7c8cb53a2ec32ac9813c24e62c21669e2923a8e9dca1aae15e9c6972b",
    "fa": "100d0e212976fc8cf1ad8625217a07a51c75240726a39856408e00a2e27bd18b",
    "fi": "b80b6ccc23e02d19267271eb095521521fbfa8ca80370cb5ccde19b4641e3b1c",
    "fr": "dc158ff1063c0012aecc5cf4194f584966694125db89b688ce282bdb0ca873c2",
    "ga": "c821ccf4c5fa04c4a951f2f797a16a548cb796f86ec1ef653d61cdb577cd3a56",
    "gl": "bb28ab2a3e4fbcf3ad81ebc47d790e94e309f1847d85a83641fd356e4d68acda",
    "gu": "ee53734ffeb0ab7ddb87b01d5bd0fea8c83441613e3b1be0c3b8d65663458e13",
    "ha": "4fe88e5bc04e357fb68bd632bdc33d135aa10ca9ce62e7a7a461784010de6335",
    "he": "41b426ed689bd524ddf3cf3bd7732894d5079bc0614525248a7432b67572eda9",
    "hi": "3e0cd20d9ff0d9bc8f44f0ae41a658d260e0148cb6582a7c21590c0111742dcc",
    "hr": "ff0d43515e198c39c4bb900272f579acc938fe86fdb6a6f9b64ee69957a49b69",
    "ht": "f30433011ad80e235f76ccd9c0c29011ac781362a39ef3a60d1de52edfb0f20c",
    "hu": "fbd58f3476b9ea50f52266a907c9b911e735fcab16839486c7e2961194660cbc",
    "id": "e99cc67e6794901c6c7f1f496ec8dc7b3e799ec9af397fbe2e19510271b930d4",
    "ig": "396c28e0a20ae99c146357ca3d99ece8f0750a508c190a5f83d3b3a5623581e3",
    "is": "bd6b39363cddb358916acd50ca8e27267c4566c412b1581e2bca895df578bc1a",
    "it": "30b0f2cd10ce01fd9bc306ee2e4012f8ee4ab846cdcaf974d66b834ac2ef7556",
    "ja": "6897447876660bcea8409539072260aeeaa6e2d62fa71a8023e848420f50fe7d",
    "ka": "8e924928c976c10e27c7401db8ac15097f700c3714b296de110118fd6dbef482",
    "kk": "3422f8dc32c26a637c03e48a138bae5d2b0178c73e4671561b70c529b81a83e0",
    "kn": "5e92e36f136178c5e1ebcb69a91d19ce8036aaaad07e5b4a26a0fc94848cb8fd",
    "ko": "35042bbfa8acebe3c20378a19a046dee6ec1d22db82bcccba59ace33f9c0a402",
    "ky": "5cd606c4c621da5fbab314f860facc01f9ccb860e7db3e06fac83b3f517ba134",
    "lo": "28dcf0f2deb6c3bd66f04f1247e9ec02d3631174eac13163a18c09c23fbf028e",
    "lt": "a7f38f6431641bae7d0959e4cbc21977665b7ad8675dbfbdf8480ae474a4b5e2",
    "lv": "d869ce3ece8c1fe1da0ac021fee2686aafb9ce7cd9c6df9e287369d28748c0ed",
    "mk": "c455edf0aa3cf1bbe8fd8f13ff39af4678470483fd90c74886dd0207c88d8009",
    "ml": "95308c44cf7b72d02e8c75bdc96fb51f73fd0e2589dceb2faa86f8e3b5da06ce",
    "mr": "6a6ccb3d9800e98477f679124a8f7f42b5cb7e599ad827b227cbc1313c370e12",
    "ms": "0184ebc8c5bbbe85a30d721b5709b01411d1f99ba07a5a762d8e7b016543b9d3",
    "nl": "92f669ca11c1353be366df98520ff757147e88996207806bc20d7629e317576a",
    "no": "45c119532e27eb486977936431e6b5a2d856c6355c59d6a4cc40b4d049524c57",
    "ny": "97349ff40bce85382f538c2610d1719f1b184ad1ddbfe17b861a2f382559cba1",
    "or": "fb3f0c79680a24477685810297d51d16705312d98a7743dd3e6185ad5f350d03",
    "pa": "10bf1f3f60e095e5c2057418efefc8f0c8011921e20a0efb1610fb74fac170a3",
    "pl": "6074282a39bcf5ee4b5a9c08f7dbf112e903de93dbdbee10b860f8d8a387f054",
    "pt": "e369d9d3be47ace30211299b7c610842d110fc4c3b465e90067aa85a17f8ebf2",
    "ro": "eed1e3d0cc6f79f174539c9fb153fe2ec3d6e01edb61b54cf1fc2b35ca09977f",
    "ru": "40335b421b9279e0602ffc644b88af9f390cbe52877eb858c80eb9ef20e881cd",
    "sk": "339115dc0ab4dead92c70301b198ed77c09ee2d8d0df337ae7e343e6ab626007",
    "sl": "e66c48dc99cc587113724255f7ae200507edd8e3ce6d0e8726be79b298a01d79",
    "sn": "041e3b349111157455fe517104f25739986ea307844940bc6f5d679724286818",
    "sq": "d18b18580f7f4a52f86d55fc33ebc7b7bf421a53bc09e54c8078ad5e2b9342c1",
    "sr": "e6bf0fd450b14021c118557caf1699aab13886fadf164dea717cad6de76de78c",
    "sv": "34232357c6353b6ed4fac2ef2cd3eb21e187f4bbe7b92d9c05cd7a2e9bfe52ad",
    "ta": "2cc2f2111809cec03f78334830ab3eaad4c818e8bde20d1fe27894bd11147a24",
    "te": "3c7ced73b3a621bcc3127e4c6334646ff6002d3a2c4738810a7fb57848503441",
    "th": "589951486845111742d12520edbfe1576fff4945befda9a6369f0267795a37ae",
    "tl": "1aff845d06d6f35f6dbe731b45e05a3dafffd51f2520fc716fd3ef18cd3f8e51",
    "tr": "cf25960ea9c366f291cf2005b743ec96ebd272851228abf8eb104f71ffe7e518",
    "uk": "0f379e6ead0d29327028a74333437024492dd02a7bf11c80ba91a4c1d3014bcd",
    "ur": "7eb95ea26888857b10834011fceacead3967f4fe07c315f19f96b1cace897142",
    "uz": "73bd2eecbd28be8a9eccccb4a343eaa0211631869ac0a68efb3d56caf7f74443",
    "vi": "6a2c64cdc2701f28aa7dcfb9eca12c51d3ff109352d8f3b5350ad31b4d5fda5c",
    "xh": "ae14395b46634390d3ee8a5b1165e48172615bc24f834339d64290615fd1cff2",
    "yo": "e076e269eb454f7a99ed7c7dd494ee4ed7fed85e9ebc6fdb31cd458802bdc6c0",
    "zh": "2f8867149dc4314e1189b549c6e19caaa0419c08feb2179e81759bf745e5caf0",
    "zu": "298ef83cf017ac7d495fcb5b03659fc91f78dc8f2cc2b3d5ae8b00989f91cd2e",
}


def lang_digest(lang: str) -> str:
    pairs = sorted((r["id"], r["text"]) for r in BANK["attacks"] + BANK["controls"] if r["lang"] == lang)
    return hashlib.sha256(json.dumps(pairs, ensure_ascii=False).encode("utf-8")).hexdigest()


check(f"every language in the bank has a pinned text digest ({len(LANG_DIGESTS)})",
      set(BANK["languages"]) == set(LANG_DIGESTS))
_moved = [lang for lang in LANG_DIGESTS if lang in BANK["languages"] and lang_digest(lang) != LANG_DIGESTS[lang]]
check(f"no language's text changed without its digest being updated{': ' + ', '.join(_moved) if _moved else ''}",
      not _moved)

check("the instrument constants are unchanged",
      BANK["canary"] == "PWNED_7F3A" and BANK["control_token"] == "CTRL_4B8E")

passed = sum(1 for _, ok in CASES if ok)
for name, ok in CASES:
    if not ok:
        print(f"  [FAIL] {name}")
print(f"{passed}/{len(CASES)} native review regression checks passed")
sys.exit(0 if passed == len(CASES) else 1)
