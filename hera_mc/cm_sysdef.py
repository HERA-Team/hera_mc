checking_order = ["parts_hera", "parts_rfi", "parts_paper", "parts_test"]
full_connection_path = {"parts_paper": ["station", "antenna", "feed", "front-end",
                                        "cable-feed75", "cable-post-amp(in)",
                                        "post-amp", "cable-post-amp(out)",
                                        "cable-receiverator", "cable-container",
                                        "f-engine"],
                        "parts_hera": ["station", "antenna", "feed", "front-end",
                                       "cable-rfof", "post-amp", "snap", "node"],
                        "parts_rfi": ["station", "antenna", "feed", "temp-cable",
                                      "snap", "node"],
                        "parts_test": ["vapor"]
                        }
corr_index = {"parts_hera": 5, "parts_paper": 9, "parts_rfi": 3},
all_pols = ["e", "n"]


def get_part_pols(part, port_query):
    """
    Given the current part and port_query (which is either 'pol' (or 'all'), 'e', or 'n')
    this figures out which pols to do.  Basically, given 'pol' and part it
    figures out whether to return ['e'], ['n'], ['e', 'n']

    Parameter:
    -----------
    part:  current part dossier
    port_query:  the ports that were requested ('e' or 'n' or 'all')
    """

    # These are parts that have their polarization as the last letter of the part name
    # There are none for HERA in the RFoF architecture
    single_pol_EN_parts = ['RI', 'RO', 'CR']
    port_groups = ['all', 'pol']
    port_query = port_query.lower()
    if port_query in port_groups:
        if part.part.hpn[:2].upper() in single_pol_EN_parts:
            return [part.part.hpn[-1].lower()]
        return all_pols

    if port_query in all_pols:
        return [port_query]
    raise ValueError('Invalid port_query')


def check_next_port(this_part, this_port, next_part, option_port, pol, lenopt):
    """
    This checks that the port is the correct one to follow through as you
    follow the hookup.
    """
    if option_port[0] == '@':
        return False

    if lenopt == 1:  # Assume the only option is correct
        return True

    if option_port.lower() in ['a', 'b']:
        p = next_part[-1].lower()
    elif option_port[0].lower() in all_pols:
        p = option_port[0].lower()
    else:
        p = pol

    return p == pol
