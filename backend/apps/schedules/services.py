from apps.accounts.models import User
from django.db.models import Q

def get_effective_members(obj):
    from apps.schedules.models import Chief, Agent, Support, ShiftAbsence, ShiftSwapRequest
    
    absent_chief_ids = set(obj.absent_chiefs.values_list("id", flat=True))
    absent_agent_ids = set(obj.absent_agents.values_list("id", flat=True))
    absent_support_ids = set(obj.absent_supports.values_list("id", flat=True))
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

    removed_chief_ids = set(obj.removed_chiefs.values_list("id", flat=True))
    removed_agent_ids = set(obj.removed_agents.values_list("id", flat=True))
    removed_support_ids = set(obj.removed_supports.values_list("id", flat=True))

    from apps.schedules.models import UserTeamTransfer
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

    chief_objs = [c for c in Chief.objects.filter(is_active=True, source_id__startswith="user:").exclude(id__in=removed_chief_ids).select_related("team").order_by("name") if get_historical_team_id(c) == obj.team_id and not is_on_vacation(c)]
    agent_objs = [a for a in Agent.objects.filter(is_active=True, source_id__startswith="user:").exclude(id__in=removed_agent_ids).select_related("team").order_by("name") if get_historical_team_id(a) == obj.team_id and not is_on_vacation(a)]
    support_objs = [s for s in Support.objects.filter(is_active=True, source_id__startswith="user:").exclude(id__in=removed_support_ids).select_related("team").order_by("name") if get_historical_team_id(s) == obj.team_id and not is_on_vacation(s)]

    chiefs = [row(item, is_absent=item.id in absent_chief_ids) for item in chief_objs]
    agents = [row(item, is_absent=item.id in absent_agent_ids) for item in agent_objs]
    supports = [row(item, is_absent=item.id in absent_support_ids) for item in support_objs]

    for item in obj.extra_chiefs.filter(is_active=True, source_id__startswith="user:"):
        if not any(m["id"] == item.id for m in chiefs):
            chiefs.append(row(item, is_extra=True, is_absent=item.id in absent_chief_ids))
    for item in obj.extra_agents.filter(is_active=True, source_id__startswith="user:"):
        if not any(m["id"] == item.id for m in agents):
            agents.append(row(item, is_extra=True, is_absent=item.id in absent_agent_ids))
    for item in obj.extra_supports.filter(is_active=True, source_id__startswith="user:"):
        if not any(m["id"] == item.id for m in supports):
            supports.append(row(item, is_extra=True, is_absent=item.id in absent_support_ids))

    manual_inclusions = [
        {
            "id": m.member_id,
            "name": m.member_name,
            "role": "Incluído manualmente",
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
    for swap in obj.swap_requests.filter(status=ShiftSwapRequest.Status.APPROVED):
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
    return members


def get_expected_member_keys(schedule):
    members_data = get_effective_members(schedule)
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
    return get_expected_member_keys(shift_schedule)
