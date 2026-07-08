CLIENT_AVATARS = [
    "chat/img/clients/client-01.png",
    "chat/img/clients/client-02.png",
    "chat/img/clients/client-03.png",
    "chat/img/clients/client-04.png",
    "chat/img/clients/client-05.png",
    "chat/img/clients/client-06.png",
    "chat/img/clients/client-07.png",
    "chat/img/clients/client-08.png",
]


def get_client_avatar_for_scenario(scenario_id: int | None) -> str:
    if not scenario_id:
        return f"/static/{CLIENT_AVATARS[0]}"

    index = (scenario_id - 1) % len(CLIENT_AVATARS)
    return f"/static/{CLIENT_AVATARS[index]}"


def get_dialog_client_avatar(dialog) -> str:
    if dialog.scenario and dialog.scenario.client_avatar:
        return dialog.scenario.client_avatar
    return get_client_avatar_for_scenario(dialog.scenario_id)


def ensure_dialog_client_avatar(dialog) -> str:
    avatar = get_dialog_client_avatar(dialog)
    if dialog.client_avatar != avatar:
        dialog.client_avatar = avatar
        dialog.save(update_fields=['client_avatar'])
    return avatar
