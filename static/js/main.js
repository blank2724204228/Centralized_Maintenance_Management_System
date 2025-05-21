// 页面加载后执行
document.addEventListener('DOMContentLoaded', function() {
    // 激活当前页面对应的导航栏项
    activateCurrentNavItem();
    
    // 任务表格搜索功能
    setupTableSearch();
    
    // 自动消失的提示信息
    setupAlertDismiss();
});

// 激活当前导航项
function activateCurrentNavItem() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

// 表格搜索功能
function setupTableSearch() {
    const searchInputs = document.querySelectorAll('.table-search-input');
    
    searchInputs.forEach(input => {
        input.addEventListener('keyup', function() {
            const searchTerm = this.value.toLowerCase();
            const tableId = this.getAttribute('data-table');
            const table = document.getElementById(tableId);
            
            if (table) {
                const rows = table.querySelectorAll('tbody tr');
                
                rows.forEach(row => {
                    const text = row.textContent.toLowerCase();
                    row.style.display = text.includes(searchTerm) ? '' : 'none';
                });
            }
        });
    });
}

// 自动消失的提示消息
function setupAlertDismiss() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    
    alerts.forEach(alert => {
        setTimeout(() => {
            const alertInstance = new bootstrap.Alert(alert);
            alertInstance.close();
        }, 3000);
    });
}

// 任务状态更新确认
function confirmStatusUpdate(taskId, status) {
    if (confirm('确定要将任务状态更新为 "' + status + '" 吗？')) {
        document.getElementById('status-form-' + taskId).submit();
    }
}

// 资源分配动态添加
function addResourceRow() {
    const container = document.getElementById('resource-rows');
    const rowCount = container.children.length;
    
    const rowTemplate = `
    <div class="row mb-3 resource-row">
        <div class="col-md-5">
            <select name="resources" class="form-select" required>
                <option value="">选择资源</option>
                ${document.querySelector('select[name="resources"]')?.innerHTML || ''}
            </select>
        </div>
        <div class="col-md-5">
            <input type="number" name="quantities" class="form-control" placeholder="数量" min="1" required>
        </div>
        <div class="col-md-2">
            <button type="button" class="btn btn-danger" onclick="removeResourceRow(this)">删除</button>
        </div>
    </div>
    `;
    
    // 创建新行元素
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = rowTemplate.trim();
    const newRow = tempDiv.firstChild;
    
    container.appendChild(newRow);
}

// 删除资源行
function removeResourceRow(button) {
    const row = button.closest('.resource-row');
    if (row) {
        row.remove();
    }
} 