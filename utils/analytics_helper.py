"""
Analytics Helper Functions - Load and analyze tracking data
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd

def load_tracking_data():
    """Load and analyze tracking logs"""
    logs_dir = "logs/activity"
    all_actions = []
    
    # Read all log files
    if os.path.exists(logs_dir):
        for filename in os.listdir(logs_dir):
            if filename.endswith('.jsonl'):
                filepath = os.path.join(logs_dir, filename)
                with open(filepath, 'r') as f:
                    for line in f:
                        try:
                            action = json.loads(line.strip())
                            all_actions.append(action)
                        except:
                            continue
    
    # Calculate metrics
    today = datetime.now().date()
    today_actions = [a for a in all_actions if datetime.fromisoformat(a['timestamp']).date() == today]
    
    # Active doctors
    active_doctors = len(set(a['doctor_id'] for a in today_actions if a['doctor_id'] != 'unknown'))
    
    # Visit metrics
    save_actions = [a for a in all_actions if a['action'] == 'visit_saved']
    total_visits = len(save_actions)
    
    # AI usage
    generate_actions = [a for a in all_actions if a['action'] == 'summary_generated']
    ai_usage_rate = 100 * len(generate_actions) / max(total_visits, 1)
    
    # Visit duration
    visit_durations = [
        a['metadata'].get('duration_seconds', 0) 
        for a in save_actions 
        if 'duration_seconds' in a.get('metadata', {})
    ]
    avg_duration = sum(visit_durations) / len(visit_durations) if visit_durations else 0
    
    # Prescription edits
    rx_edits = [a for a in all_actions if a['action'] == 'prescription_edited']
    rx_edit_rate = 100 * len(rx_edits) / max(len(generate_actions), 1)
    
    # Alerts
    alerts_shown = [a for a in all_actions if a['action'] == 'alert_shown']
    alerts_accepted = [a for a in all_actions if a['action'] == 'alert_accepted']
    alert_acceptance = 100 * len(alerts_accepted) / max(len(alerts_shown), 1)
    
    # WhatsApp (keeping for backward compatibility even though removed)
    whatsapp_sent = [a for a in all_actions if a['action'] == 'whatsapp_sent']
    whatsapp_rate = 100 * len(whatsapp_sent) / max(total_visits, 1)
    
    # Format preference
    format_uses = [a for a in all_actions if a['action'] == 'summary_generated']
    soap_count = sum(1 for a in format_uses if a.get('metadata', {}).get('format') == 'SOAP')
    indian_count = sum(1 for a in format_uses if a.get('metadata', {}).get('format') == 'INDIAN_EMR')
    preferred_format = "SOAP" if soap_count > indian_count else "INDIAN_EMR"
    
    return {
        'active_doctors_today': active_doctors,
        'total_visits': total_visits,
        'avg_visit_duration': avg_duration,
        'ai_usage_rate': ai_usage_rate,
        'rx_edit_rate': rx_edit_rate,
        'alert_acceptance': alert_acceptance,
        'whatsapp_rate': whatsapp_rate,
        'preferred_format': preferred_format,
        'total_actions': len(all_actions),
        'today_actions': len(today_actions)
    }

def get_doctor_personal_stats(doctor_id: str):
    """Get stats for individual doctor"""
    logs_dir = "logs/activity"
    doctor_actions = []
    
    # Read all log files for this doctor
    if os.path.exists(logs_dir):
        for filename in os.listdir(logs_dir):
            if filename.endswith('.jsonl'):
                filepath = os.path.join(logs_dir, filename)
                with open(filepath, 'r') as f:
                    for line in f:
                        try:
                            action = json.loads(line.strip())
                            if action.get('doctor_id') == doctor_id:
                                doctor_actions.append(action)
                        except:
                            continue
    
    # Calculate metrics
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    today_visits = len([
        a for a in doctor_actions 
        if a['action'] == 'visit_saved' and 
        datetime.fromisoformat(a['timestamp']).date() == today
    ])
    
    week_visits = len([
        a for a in doctor_actions 
        if a['action'] == 'visit_saved' and 
        datetime.fromisoformat(a['timestamp']).date() >= week_ago
    ])
    
    total_visits = len([a for a in doctor_actions if a['action'] == 'visit_saved'])
    
    # AI usage rate
    summaries = len([a for a in doctor_actions if a['action'] == 'summary_generated'])
    ai_usage = 100 * summaries / max(total_visits, 1)
    
    return {
        'today_count': today_visits,
        'week_count': week_visits,
        'total_count': total_visits,
        'ai_usage_rate': round(ai_usage, 1)
    }

def get_daily_visit_chart_data():
    """Get daily visit counts for chart"""
    logs_dir = "logs/activity"
    all_visits = []
    
    if os.path.exists(logs_dir):
        for filename in os.listdir(logs_dir):
            if filename.endswith('.jsonl'):
                filepath = os.path.join(logs_dir, filename)
                with open(filepath, 'r') as f:
                    for line in f:
                        try:
                            action = json.loads(line.strip())
                            if action['action'] == 'visit_saved':
                                all_visits.append(action)
                        except:
                            continue
    
    # Group by date
    visit_dates = {}
    for visit in all_visits:
        date = datetime.fromisoformat(visit['timestamp']).date()
        date_str = date.strftime('%Y-%m-%d')
        visit_dates[date_str] = visit_dates.get(date_str, 0) + 1
    
    # Create DataFrame for last 30 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    dates = []
    counts = []
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        dates.append(date_str)
        counts.append(visit_dates.get(date_str, 0))
        current_date += timedelta(days=1)
    
    if dates and counts:
        df = pd.DataFrame({'date': dates, 'visits': counts})
        df.set_index('date', inplace=True)
        return df
    else:
        return pd.DataFrame()

def get_doctor_leaderboard():
    """Get doctor activity leaderboard"""
    logs_dir = "logs/activity"
    doctor_stats = {}
    
    if os.path.exists(logs_dir):
        for filename in os.listdir(logs_dir):
            if filename.endswith('.jsonl'):
                filepath = os.path.join(logs_dir, filename)
                with open(filepath, 'r') as f:
                    for line in f:
                        try:
                            action = json.loads(line.strip())
                            doctor_id = action.get('doctor_id', 'unknown')
                            
                            if doctor_id != 'unknown':
                                if doctor_id not in doctor_stats:
                                    doctor_stats[doctor_id] = {
                                        'visits': 0,
                                        'ai_summaries': 0,
                                        'rx_edits': 0,
                                        'pdf_exports': 0,
                                        'docx_exports': 0
                                    }
                                
                                if action['action'] == 'visit_saved':
                                    doctor_stats[doctor_id]['visits'] += 1
                                elif action['action'] == 'summary_generated':
                                    doctor_stats[doctor_id]['ai_summaries'] += 1
                                elif action['action'] == 'prescription_edited':
                                    doctor_stats[doctor_id]['rx_edits'] += 1
                                elif action['action'] == 'pdf_exported':
                                    doctor_stats[doctor_id]['pdf_exports'] += 1
                                elif action['action'] == 'docx_exported':
                                    doctor_stats[doctor_id]['docx_exports'] += 1
                        except:
                            continue
    
    # Convert to DataFrame
    if doctor_stats:
        df = pd.DataFrame.from_dict(doctor_stats, orient='index')
        df['AI Usage %'] = (df['ai_summaries'] / df['visits'].clip(lower=1) * 100).round(1)
        df['Rx Edit %'] = (df['rx_edits'] / df['ai_summaries'].clip(lower=1) * 100).round(1)
        df = df.sort_values('visits', ascending=False)
        df.index.name = 'Doctor'
        return df
    else:
        return pd.DataFrame()

def get_recent_actions(limit: int = 100):
    """Get recent raw actions for debugging"""
    logs_dir = "logs/activity"
    all_actions = []
    
    if os.path.exists(logs_dir):
        # Get all log files sorted by modification time
        log_files = []
        for filename in os.listdir(logs_dir):
            if filename.endswith('.jsonl'):
                filepath = os.path.join(logs_dir, filename)
                log_files.append((filepath, os.path.getmtime(filepath)))
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x[1], reverse=True)
        
        # Read from newest files until we have enough actions
        for filepath, _ in log_files:
            if len(all_actions) >= limit:
                break
                
            with open(filepath, 'r') as f:
                lines = f.readlines()
                # Read from end of file
                for line in reversed(lines):
                    if len(all_actions) >= limit:
                        break
                    try:
                        action = json.loads(line.strip())
                        all_actions.append(action)
                    except:
                        continue
    
    return all_actions[:limit]

def get_feature_usage_stats():
    """Get detailed feature usage statistics"""
    logs_dir = "logs/activity"
    feature_counts = {
        'voice_input': 0,
        'pdf_export': 0,
        'docx_export': 0,  # Added Word export tracking
        'whatsapp': 0,
        'lab_upload': 0,
        'backdated_entry': 0,
        'format_soap': 0,
        'format_indian': 0,
        'vitals_entered': 0,
        'prescription_included': 0
    }
    
    if os.path.exists(logs_dir):
        for filename in os.listdir(logs_dir):
            if filename.endswith('.jsonl'):
                filepath = os.path.join(logs_dir, filename)
                with open(filepath, 'r') as f:
                    for line in f:
                        try:
                            action = json.loads(line.strip())
                            
                            # Count feature usage
                            if action['action'] == 'voice_input_used':
                                feature_counts['voice_input'] += 1
                            elif action['action'] == 'pdf_exported':
                                feature_counts['pdf_export'] += 1
                            elif action['action'] == 'docx_exported':
                                feature_counts['docx_export'] += 1
                            elif action['action'] == 'whatsapp_sent':
                                feature_counts['whatsapp'] += 1
                            elif action['action'] == 'lab_uploaded':
                                feature_counts['lab_upload'] += 1
                            elif action['action'] == 'backdated_entry':
                                feature_counts['backdated_entry'] += 1
                            elif action['action'] == 'summary_generated':
                                meta = action.get('metadata', {})
                                if meta.get('format') == 'SOAP':
                                    feature_counts['format_soap'] += 1
                                elif meta.get('format') == 'INDIAN_EMR':
                                    feature_counts['format_indian'] += 1
                                if meta.get('has_prescription'):
                                    feature_counts['prescription_included'] += 1
                            elif action['action'] == 'vitals_entered':
                                feature_counts['vitals_entered'] += 1
                        except:
                            continue
    
    return feature_counts