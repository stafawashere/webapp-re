def fetch_members(client, member_ids):
   members = []

   for member_id in member_ids:
      members.append(client.get_member(member_id))

   return members
