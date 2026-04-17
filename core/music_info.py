def parse_song_info(filename):
    stem = Path(filename).stem
    pattern = r'^(.+?)\s*[---]\s*(.+)$'
    match = re.match(pattern,stem.strip())

    if match:
        return{
            'artist':match.group(1).strip(),
            'title':match.group(2).strip()
        }
    return {'artist':'','title':stem.strip()}
