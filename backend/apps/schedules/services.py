from apps.accounts.models import User
from django.db.models import Q


SHIFT_SCHEDULE_STAFF_SOURCE = "SHIFT_SCHEDULE"
LEGACY_SERVICE_ORDER_STAFF_SOURCE = "LEGACY_SERVICE_ORDER"
MISSING_SHIFT_SCHEDULE_STAFF_SOURCE = "MISSING_SHIFT_SCHEDULE"


def resolve_shift_schedule_for_agenda(agenda, schedule_map=None):
    from apps.schedules.models import ShiftSchedule

    if agenda is None or getattr(agenda, "service_order_mode", None) == getattr(agenda.ServiceOrderMode, "DESIGNATED", "DESIGNATED"):
        return None

    team_id = getattr(agenda, "team_ref_id", None)
    if team_id:
        key = (agenda.date, team_id)
        if schedule_map is not None and key in schedule_map:
            return schedule_map[key]
        return (
            ShiftSchedule.objects.filter(date=agenda.date, team_id=team_id)
            .select_related("team")
            .prefetch_related(
                "extra_chiefs",
                "extra_agents",
                "extra_supports",
                "removed_chiefs",
                "removed_agents",
                "removed_supports",
                "absent_chiefs",
                "absent_agents",
                "absent_supports",
                "absence_records",
                "manual_inclusions",
                "swap_requests",
                "swap_requests__target_team",
            )
            .first()
        )

    team_name = str(getattr(agenda, "team_name", "") or "").strip()
    if not team_name:
        return None
    return (
        ShiftSchedule.objects.filter(date=agenda.date, team__name__iexact=team_name)
        .select_related("team")
        .prefetch_related(
            "extra_chiefs",
            "extra_agents",
            "extra_supports",
            "removed_chiefs",
            "removed_agents",
            "removed_supports",
            "absent_chiefs",
            "absent_agents",
            "absent_supports",
            "absence_records",
            "manual_inclusions",
            "swap_requests",
            "swap_requests__target_team",
        )
        .first()
    )


def build_legacy_agenda_staff(agenda):
    def legacy_member(member_id, name, *, member_type, team_id=None, team_name=""):
        return {
            "id": member_id,
            "source_id": None,
            "name": name,
            "role": member_type,
            "cpf": "",
            "team": team_id,
            "team_name": team_name or "Sem equipe",
            "is_extra": False,
            "is_absent": False,
            "absence_reason": "",
            "absence_attachment_url": "",
            "is_legacy": True,
        }

    team_id = getattr(agenda, "team_ref_id", None)
    team_name = getattr(getattr(agenda, "team_ref", None), "name", "") or getattr(agenda, "team_name", "") or ""
    chiefs = []
    if getattr(agenda, "chief_ref_id", None):
        chief = getattr(agenda, "chief_ref", None)
        chiefs.append(
            legacy_member(
                agenda.chief_ref_id,
                getattr(chief, "name", "") or getattr(agenda, "chief_name", ""),
                member_type="Chefe",
                team_id=team_id,
                team_name=team_name,
            )
        )
    elif str(getattr(agenda, "chief_name", "") or "").strip():
        chiefs.append(
            legacy_member(
                None,
                str(agenda.chief_name).strip(),
                member_type="Chefe",
                team_id=team_id,
                team_name=team_name,
            )
        )

    agents = []
    agenda_agent_refs = list(agenda.agents_ref.all()) if hasattr(agenda, "agents_ref") else []
    if agenda_agent_refs:
        for agent in agenda_agent_refs:
            agents.append(
                legacy_member(
                    agent.id,
                    agent.name,
                    member_type="Agente",
                    team_id=getattr(agent, "team_id", team_id),
                    team_name=getattr(getattr(agent, "team", None), "name", "") or team_name,
                )
            )
    else:
        raw_agents = [part.strip() for part in str(getattr(agenda, "agents", "") or "").split(" - ") if part.strip()]
        for agent_name in raw_agents:
            agents.append(
                legacy_member(
                    None,
                    agent_name,
                    member_type="Agente",
                    team_id=team_id,
                    team_name=team_name,
                )
            )

    supports = []
    for support_ref_attr, support_name_attr in (("support_1_ref", "support_1"), ("support_2_ref", "support_2")):
        support_ref = getattr(agenda, support_ref_attr, None)
        support_name = getattr(agenda, support_name_attr, "")
        if support_ref:
            supports.append(
                legacy_member(
                    support_ref.id,
                    support_ref.name,
                    member_type="Apoio",
                    team_id=getattr(support_ref, "team_id", team_id),
                    team_name=getattr(getattr(support_ref, "team", None), "name", "") or team_name,
                )
            )
        elif str(support_name or "").strip():
            supports.append(
                legacy_member(
                    None,
                    str(support_name).strip(),
                    member_type="Apoio",
                    team_id=team_id,
                    team_name=team_name,
                )
            )

    return {
        "chiefs": chiefs,
        "agents": agents,
        "supports": supports,
        "manual": [],
        "context_resolved": False,
        "legacy_fallback": True,
    }


def get_agenda_effective_staff_payload(agenda, schedule=None, schedule_map=None):
    mode = getattr(agenda, "service_order_mode", None) or getattr(agenda.ServiceOrderMode, "TEAM", "TEAM")
    if mode == getattr(agenda.ServiceOrderMode, "DESIGNATED", "DESIGNATED"):
        return {
            "staff_source": None,
            "staff_source_label": "",
            "shift_schedule_id": None,
            "shift_schedule_missing": False,
            "effective_staff": None,
            "effective_staff_warning": "",
        }

    resolved_schedule = schedule or resolve_shift_schedule_for_agenda(agenda, schedule_map=schedule_map)
    if resolved_schedule is not None:
        return {
            "staff_source": SHIFT_SCHEDULE_STAFF_SOURCE,
            "staff_source_label": "Escala",
            "shift_schedule_id": resolved_schedule.id,
            "shift_schedule_missing": False,
            "effective_staff": get_effective_members(resolved_schedule, agenda),
            "effective_staff_warning": "",
        }

    return {
        "staff_source": LEGACY_SERVICE_ORDER_STAFF_SOURCE if getattr(agenda, "id", None) else MISSING_SHIFT_SCHEDULE_STAFF_SOURCE,
        "staff_source_label": "Ordem de Serviço legada",
        "shift_schedule_id": None,
        "shift_schedule_missing": True,
        "effective_staff": build_legacy_agenda_staff(agenda),
        "effective_staff_warning": "Efetivo não localizado na Escala para esta data.",
    }


def get_effective_members(obj, agenda=None):
    from apps.schedules.models import Chief, Agent, Support, ShiftAbsence, ShiftSwapRequest

    # The team's operational roster is the active account-linked lookup record.
    # Imported and legacy lookups participate only when explicitly added as extras.
    def related_items(relation_name):
        return list(getattr(obj, relation_name).all())

    absent_chief_ids = {member.id for member in related_items("absent_chiefs")}
    absent_agent_ids = {member.id for member in related_items("absent_agents")}
    absent_support_ids = {member.id for member in related_items("absent_supports")}
    absence_records = {
        (record.member_type, record.member_id): record
        for record in obj.absence_records.all()
    }

    def row(item, is_extra=False, is_absent=False):
        member_type = None
        if isinstance(item, Chief):
            member_type = ShiftAbsence.MemberType.CHIEF
        elif isinstance(item, Support):
            member_type = ShiftAbsence.MemberType.SUPPORT
        else:
            member_type = ShiftAbsence.MemberType.AGENT
        absence = absence_records.get((member_type, item.id))
        return {
            "id": item.id,
            "source_id": getattr(item, "source_id", None),
            "name": item.name,
            "role": item.role,
            "cpf": item.cpf,
            "team": item.team_id,
            "team_name": item.team.name if item.team else "Sem equipe",
            "is_extra": is_extra,
            "is_absent": is_absent,
            "absence_reason": absence.reason if absence else "",
            "absence_attachment_url": absence.attachment.url if absence and absence.attachment else "",
        }

    removed_chief_ids = {member.id for member in related_items("removed_chiefs")}
    removed_agent_ids = {member.id for member in related_items("removed_agents")}
    removed_support_ids = {member.id for member in related_items("removed_supports")}

    from apps.schedules.models import UserTeamTransfer
    staff_context = getattr(obj, "_effective_staff_context", None) or {}
    transfers = staff_context.get("transfers")
    if transfers is None:
        transfers = list(UserTeamTransfer.objects.order_by("effective_date"))

    def get_historical_team_id(item):
        if not item.source_id or not item.source_id.startswith("user:"):
            return item.team_id
        try:
            user_id = int(item.source_id.split(":")[1])
        except ValueError:
            return item.team_id
        
        future_transfers = [t for t in transfers if t.user_id == user_id and t.effective_date > obj.date]
        if future_transfers:
            return future_transfers[0].old_team_id
        return item.team_id

    def is_on_vacation(item):
        if item.vacation_start and item.vacation_end:
            return item.vacation_start <= obj.date <= item.vacation_end
        return False

    def base_members(model, attribute, removed_ids):
        prefetched = getattr(obj.team, attribute, None)
        if prefetched is None:
            prefetched = model.objects.filter(
                is_active=True,
                source_id__startswith="user:",
            ).select_related("team").order_by("name")
        return [
            member for member in prefetched
            if member.id not in removed_ids
            and get_historical_team_id(member) == obj.team_id
            and not is_on_vacation(member)
        ]

    chief_objs = base_members(Chief, "_shift_schedule_chiefs", removed_chief_ids)
    agent_objs = base_members(Agent, "_shift_schedule_agents", removed_agent_ids)
    support_objs = base_members(Support, "_shift_schedule_supports", removed_support_ids)

    chiefs = [row(item, is_absent=item.id in absent_chief_ids) for item in chief_objs]
    agents = [row(item, is_absent=item.id in absent_agent_ids) for item in agent_objs]
    supports = [row(item, is_absent=item.id in absent_support_ids) for item in support_objs]

    for item in related_items("extra_chiefs"):
        if not item.is_active:
            continue
        if item.id not in removed_chief_ids and not any(m["id"] == item.id for m in chiefs):
            chiefs.append(row(item, is_extra=True, is_absent=item.id in absent_chief_ids))
    for item in related_items("extra_agents"):
        if not item.is_active:
            continue
        if item.id not in removed_agent_ids and not any(m["id"] == item.id for m in agents):
            agents.append(row(item, is_extra=True, is_absent=item.id in absent_agent_ids))
    for item in related_items("extra_supports"):
        if not item.is_active:
            continue
        if item.id not in removed_support_ids and not any(m["id"] == item.id for m in supports):
            supports.append(row(item, is_extra=True, is_absent=item.id in absent_support_ids))

    def normalize_cpf(value):
        return "".join(character for character in str(value or "") if character.isdigit())

    def get_keys(item):
        cpf = item.get("cpf")
        source_id = item.get("source_id")
        normalized_cpf = normalize_cpf(cpf)
        cpf_key = f"cpf:{normalized_cpf}" if normalized_cpf else None
        source_key = f"source:{source_id}" if source_id else None
        return cpf_key, source_key

    def cpf_variants(value):
        normalized = normalize_cpf(value)
        variants = {value, normalized} if value else {normalized}
        if len(normalized) == 11:
            variants.add(f"{normalized[:3]}.{normalized[3:6]}.{normalized[6:9]}-{normalized[9:]}")
        return {variant for variant in variants if variant}

    user_ids = set()
    cpf_values = set()
    for member in agents + supports:
        cpf_key, source_key = get_keys(member)
        if source_key and source_key.startswith("source:user:"):
            try:
                user_ids.add(int(source_key.split(":")[-1]))
            except ValueError:
                pass
        if cpf_key:
            cpf_values.update(cpf_variants(member.get("cpf")))

    active_users = staff_context.get("active_users")
    if active_users is None:
        active_user_filter = Q()
        if user_ids:
            active_user_filter |= Q(id__in=user_ids)
        if cpf_values:
            active_user_filter |= Q(cpf__in=cpf_values)
        active_users = User.objects.filter(active_user_filter, is_active=True) if active_user_filter else User.objects.none()
    role_by_source = {f"source:user:{user.id}": user.role for user in active_users}
    role_by_cpf = {
        f"cpf:{normalize_cpf(user.cpf)}": user.role
        for user in active_users
        if normalize_cpf(user.cpf)
    }

    def get_active_role(member):
        cpf_key, source_key = get_keys(member)
        if source_key and source_key in role_by_source:
            return role_by_source[source_key]
        if cpf_key and cpf_key in role_by_cpf:
            return role_by_cpf[cpf_key]
        return None

    def is_agent_role(role):
        return role == User.Role.USER

    def is_support_role(role):
        return role == User.Role.SUPPORT

    def deduplicate_group(group_items):
        final = []
        keys = set()
        for item in group_items:
            cpf_key, source_key = get_keys(item)
            if (cpf_key and cpf_key in keys) or (source_key and source_key in keys):
                continue
            final.append(item)
            if cpf_key:
                keys.add(cpf_key)
            if source_key:
                keys.add(source_key)
        return final

    chiefs = deduplicate_group(chiefs)
    supports = deduplicate_group([
        support for support in supports
        if not is_agent_role(get_active_role(support))
    ])
    agents = deduplicate_group([
        agent for agent in agents
        if not is_support_role(get_active_role(agent))
    ])
    manual_inclusions = [
        {
            "id": m.member_id,
            "name": m.member_name,
            "role": "Inclu\u00eddo manualmente",
            "member_type": m.member_type,
            "is_manual": True,
            "is_absent": absence_records.get((m.member_type, m.member_id)) is not None,
            "absence_reason": absence_records.get((m.member_type, m.member_id)).reason if absence_records.get((m.member_type, m.member_id)) else "",
        }
        for m in obj.manual_inclusions.all()
    ]

    members = {
        "chiefs": chiefs,
        "agents": agents,
        "supports": supports,
        "manual": manual_inclusions,
    }
    for swap in (
        swap for swap in obj.swap_requests.all()
        if swap.status == ShiftSwapRequest.Status.APPROVED
    ):
        group = {
            ShiftSwapRequest.MemberType.CHIEF: "chiefs",
            ShiftSwapRequest.MemberType.AGENT: "agents",
            ShiftSwapRequest.MemberType.SUPPORT: "supports",
        }.get(swap.member_type, "agents")

        is_swap_absent = False
        if swap.member_type == ShiftSwapRequest.MemberType.CHIEF:
            is_swap_absent = swap.to_member_id in absent_chief_ids
        elif swap.member_type == ShiftSwapRequest.MemberType.SUPPORT:
            is_swap_absent = swap.to_member_id in absent_support_ids
        else:
            is_swap_absent = swap.to_member_id in absent_agent_ids
        swap_absence = absence_records.get((swap.member_type, swap.to_member_id))

        replacement = {
            "id": f"swap-{swap.id}",
            "real_id": swap.to_member_id,
            "name": swap.to_member_name,
            "role": f"Troca aprovada: substitui {swap.from_member_name}",
            "cpf": "",
            "team": swap.target_team_id,
            "team_name": swap.target_team.name,
            "swapped": True,
            "is_swap": True,
            "swap_for": swap.from_member_name,
            "is_absent": is_swap_absent,
            "absence_reason": swap_absence.reason if swap_absence else "",
            "absence_attachment_url": swap_absence.attachment.url if swap_absence and swap_absence.attachment else "",
        }
        for index, member in enumerate(members[group]):
            if str(member["id"]) == str(swap.from_member_id):
                members[group][index] = replacement
                break
        else:
            members[group].append(replacement)
    members["context_resolved"] = agenda is not None
    return members


def get_expected_member_keys(schedule, agenda=None):
    members_data = get_effective_members(schedule, agenda)
    expected_members = set()
    for c in members_data.get("chiefs", []):
        expected_members.add(f"CHIEF_{c['id']}")
    for a in members_data.get("agents", []):
        expected_members.add(f"AGENT_{a['id']}")
    for s in members_data.get("supports", []):
        expected_members.add(f"SUPPORT_{s['id']}")
    return expected_members


def _attendance_digits(value):
    return "".join(char for char in str(value or "") if char.isdigit())


def _find_lookup_for_user(model, user):
    source_id = f"user:{user.id}"
    lookup = model.objects.filter(source_id=source_id, is_active=True).select_related("team").first()
    if lookup:
        return lookup
    cpf = _attendance_digits(getattr(user, "cpf", ""))
    if cpf:
        formatted = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else cpf
        lookup = model.objects.filter(Q(cpf=cpf) | Q(cpf=formatted), is_active=True).select_related("team").first()
        if lookup:
            return lookup
    full_name = str(getattr(user, "full_name", "") or "").strip()
    if full_name:
        return model.objects.filter(name__iexact=full_name, is_active=True).select_related("team").first()
    return None


def member_key_from_user(user):
    from apps.schedules.models import Chief, Agent, Support

    candidates = []
    if getattr(user, "role", "") == User.Role.SUPERVISOR:
        candidates = [(Chief, "CHIEF"), (Agent, "AGENT"), (Support, "SUPPORT")]
    elif getattr(user, "role", "") == User.Role.SUPPORT:
        candidates = [(Support, "SUPPORT"), (Agent, "AGENT"), (Chief, "CHIEF")]
    else:
        candidates = [(Agent, "AGENT"), (Support, "SUPPORT"), (Chief, "CHIEF")]

    for model, prefix in candidates:
        lookup = _find_lookup_for_user(model, user)
        if lookup:
            return f"{prefix}_{lookup.id}"
    return None


def get_expected_attendance_member_keys(agenda, shift_schedule=None):
    mode = getattr(agenda, "service_order_mode", None) or getattr(agenda.ServiceOrderMode, "TEAM", "TEAM")
    if mode == getattr(agenda.ServiceOrderMode, "DESIGNATED", "DESIGNATED"):
        expected = set()
        for user in agenda.designated_users.filter(is_active=True):
            key = member_key_from_user(user)
            if key:
                expected.add(key)
        return expected
    if shift_schedule is None:
        return set()
    return get_expected_member_keys(shift_schedule, agenda)
