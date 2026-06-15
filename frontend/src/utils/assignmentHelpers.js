export function getAssignedAgentLabel(ticket) {
  if (!ticket) {
    return 'Unassigned';
  }
  if (ticket.assigned_agent_email) {
    return ticket.assigned_agent_email;
  }
  if (ticket.assigned_agent_name) {
    return ticket.assigned_agent_name;
  }
  if (ticket.assigned_agent_id) {
    return ticket.assigned_agent_id;
  }
  return 'Unassigned';
}

export function formatAgentOptionLabel(agent) {
  if (agent.email && agent.name) {
    return `${agent.name} (${agent.email})`;
  }
  return agent.email || agent.name || agent.id;
}
